from django.db import models
from django.contrib.auth.models import User


class Place(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    place_type = models.CharField(max_length=100, blank=True)  # cafe, bar, park etc

    def __str__(self):
        return self.name


class Checkin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkins')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='checkins')
    message = models.CharField(max_length=200, blank=True)  # "studying here!" or "grabbing a beer"
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # checkins expire after ~2 hours

    def __str__(self):
        return f"{self.user.username} @ {self.place.name}"


class Friendship(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')  # can't add same friend twice

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username}"


class PointEvent(models.Model):
    REASON_CHOICES = [
        ('new_place', 'Checked in to a new place'),
        ('repeat_place', 'Checked in to a familiar place'),
        ('friend_joined', 'A friend joined you'),
        ('new_type', 'Explored a new type of place'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_events')
    checkin = models.ForeignKey(Checkin, on_delete=models.CASCADE, related_name='point_events')
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} +{self.points} ({self.reason})"
