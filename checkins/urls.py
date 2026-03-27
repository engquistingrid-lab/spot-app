from django.urls import path
from . import views

urlpatterns = [
    path('places/', views.PlaceListCreateView.as_view(), name='places'),
    path('checkins/', views.CheckinCreateView.as_view(), name='checkin-create'),
    path('feed/', views.FeedView.as_view(), name='feed'),
    path('places/<int:place_id>/active/', views.ActiveAtPlaceView.as_view(), name='active-at-place'),
    path('friends/<int:user_id>/add/', views.AddFriendView.as_view(), name='add-friend'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]