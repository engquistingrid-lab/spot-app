from django.views import View
from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from .models import Place, Checkin, Friendship, PointEvent
from .serializers import (
    PlaceSerializer, CheckinSerializer,
    FriendshipSerializer, PointEventSerializer, UserSerializer
)


def calculate_points(user, place, checkin):
    points_earned = 0

    # has this user checked in here before?
    previous_visits = Checkin.objects.filter(
        user=user, place=place
    ).exclude(id=checkin.id).count()

    if previous_visits == 0:
        # brand new place — big points
        PointEvent.objects.create(
            user=user, checkin=checkin,
            reason='new_place', points=10
        )
        points_earned += 10
    else:
        # familiar place — small points
        PointEvent.objects.create(
            user=user, checkin=checkin,
            reason='repeat_place', points=3
        )
        points_earned += 3

    # has the user visited this type of place before?
    if place.place_type:
        same_type_visits = Checkin.objects.filter(
            user=user, place__place_type=place.place_type
        ).exclude(id=checkin.id).count()

        if same_type_visits == 0:
            PointEvent.objects.create(
                user=user, checkin=checkin,
                reason='new_type', points=5
            )
            points_earned += 5

    return points_earned


class PlaceListCreateView(generics.ListCreateAPIView):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Best-effort de-dupe: if a Place with the same name (and optionally type)
        already exists very close to the provided coordinates, reuse it.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        name = (data.get('name') or '').strip()
        lat = data.get('latitude')
        lng = data.get('longitude')
        place_type = (data.get('place_type') or '').strip()

        # ~50-100m-ish bounding box depending on latitude.
        delta = 0.0008
        existing_qs = Place.objects.filter(
            name__iexact=name,
            latitude__gte=lat - delta,
            latitude__lte=lat + delta,
            longitude__gte=lng - delta,
            longitude__lte=lng + delta,
        )
        if place_type:
            existing_qs = existing_qs.filter(place_type__iexact=place_type)

        existing = existing_qs.order_by('id').first()
        if existing:
            out = self.get_serializer(existing)
            return Response(out.data, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CheckinCreateView(generics.CreateAPIView):
    serializer_class = CheckinSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # checkin expires after 2 hours
        expires_at = timezone.now() + timedelta(hours=2)
        checkin = serializer.save(user=self.request.user, expires_at=expires_at)
        calculate_points(self.request.user, checkin.place, checkin)


class FeedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        friend_ids = list(Friendship.objects.filter(
            from_user=request.user
        ).values_list('to_user_id', flat=True))
        
        # include yourself so you can see your own checkins
        friend_ids.append(request.user.id)

        now = timezone.now()
        checkins = Checkin.objects.filter(
            user_id__in=friend_ids,
            expires_at__gt=now
        ).select_related('user', 'place').order_by('-created_at')

        serializer = CheckinSerializer(checkins, many=True)
        return Response(serializer.data)

class ActiveAtPlaceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, place_id):
        # who is currently checked in at this place?
        now = timezone.now()
        checkins = Checkin.objects.filter(
            place_id=place_id,
            expires_at__gt=now
        ).select_related('user', 'place')

        serializer = CheckinSerializer(checkins, many=True)
        return Response(serializer.data)


class AddFriendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        try:
            to_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if to_user == request.user:
            return Response({'error': 'You cannot add yourself'}, status=400)

        friendship, created = Friendship.objects.get_or_create(
            from_user=request.user,
            to_user=to_user
        )

        if not created:
            return Response({'error': 'Already friends'}, status=400)

        return Response({'message': f'You are now friends with {to_user.username}'})


class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # get friend IDs including yourself
        friend_ids = list(Friendship.objects.filter(
            from_user=request.user
        ).values_list('to_user_id', flat=True))
        friend_ids.append(request.user.id)

        # sum points per user
        from django.db.models import Sum
        leaderboard = (
            PointEvent.objects
            .filter(user_id__in=friend_ids)
            .values('user__username')
            .annotate(total_points=Sum('points'))
            .order_by('-total_points')
        )

        return Response(list(leaderboard))
    


class MapView(View):
    def get(self, request):
        return render(request, 'checkins/map.html')
class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=400
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already taken'},
                status=400
            )

        user = User.objects.create_user(username=username, password=password)

        # automatically log them in by returning a token
        refresh = RefreshToken.for_user(user)
        return Response({
            'username': user.username,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=201)