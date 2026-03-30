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
        # get all friend IDs
        friend_ids = Friendship.objects.filter(
            from_user=request.user
        ).values_list('to_user_id', flat=True)

        # get their active checkins (not expired)
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
    
class MapView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return render(request, 'checkins/map.html')