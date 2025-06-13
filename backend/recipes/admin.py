from django.contrib import admin

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1
    max_num = 10000
    fields = ('ingredient', 'amount')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'cooking_time', 'favorites_count')
    search_fields = ('name', 'author__username')
    inlines = [RecipeIngredientInline]

    @admin.display(description="Добавлений в избранное")
    def favorites_count(self, obj):
        return obj.favorites.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')