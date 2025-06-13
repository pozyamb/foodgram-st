from django.urls import include, path
from rest_framework import routers

import api.views as vs

user_router = routers.DefaultRouter()
recipe_router = routers.DefaultRouter()

user_router.register(
    'users',
    vs.UserViewSet,
    basename='users'
)

recipe_router.register(
    'ingredients',
    vs.IngredientViewSet,
    basename='ingredients'
)

recipe_router.register(
    'recipes',
    vs.RecipeViewSet,
    basename='recipes'
)

urlpatterns = [
    path('', include(user_router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(recipe_router.urls)),
]