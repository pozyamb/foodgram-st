import django_filters
from recipes.models import Recipe
from django_filters.rest_framework import BooleanFilter


class RecipeFilter(django_filters.FilterSet):
    is_favorited = BooleanFilter(method='filter_favorites')
    is_in_shopping_cart = BooleanFilter(method='filter_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author']

    def filter_favorites(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset