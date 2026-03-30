from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Place, Checkin, Friendship, PointEvent


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'place_type']


class CheckinSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    place = PlaceSerializer(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(
        queryset=Place.objects.all(), source='place', write_only=True
    )

    class Meta:
        model = Checkin
        fields = ['id', 'user', 'place', 'place_id', 'message', 'created_at', 'expires_at']


class FriendshipSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'from_user', 'to_user', 'created_at']


class PointEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointEvent
        fields = ['id', 'reason', 'points', 'created_at']