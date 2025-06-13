from rest_framework import serializers as slz
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework.exceptions import ValidationError
from api.abstractions.serializers import BaseUserRecipeSerializer
from api.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart)
from users.models import Follow

User = get_user_model()


class UserSerializer(DjoserUserSerializer):
    is_subscribed = slz.SerializerMethodField()
    avatar = slz.ImageField(required=False, allow_null=True)

    class Meta(DjoserUserSerializer.Meta):
        fields = DjoserUserSerializer.Meta.fields + ('is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and obj.follower.filter(user=user).exists()
        )

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class RecipeIngredientSerializer(slz.ModelSerializer):
    id = slz.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = slz.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']


class IngredientSerializer(slz.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeReadSerializer(slz.ModelSerializer):
    is_favorited = slz.SerializerMethodField()
    is_in_shopping_cart = slz.SerializerMethodField()
    author = UserSerializer(read_only=True)
    ingredients = slz.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time',
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and obj.shopping_carts.filter(user=user).exists()
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and obj.favorites.filter(user=user).exists()
        )

    def get_ingredients(self, obj):
        ingredients = []
        for recipe_ingredient in obj.recipe_ingredients.all():
            ingredient_data = IngredientSerializer(
                recipe_ingredient.ingredient).data
            ingredient_data['amount'] = recipe_ingredient.amount
            ingredients.append(ingredient_data)
        return ingredients


class RecipeWriteSerializer(slz.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True, write_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('name', 'image', 'text', 'ingredients', 'cooking_time')

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data

    def validate_cooking_time(self, value):
        if value < 2:
            raise ValidationError(
                {
                    "cooking_time": [
                        "Время готовки не может быть меньше 2 мин."
                    ]
                }
            )
        return value

    def validate(self, data):
        ingredients_data = data.get('ingredients', [])

        if not ingredients_data:
            raise ValidationError(
                {"ingredients": ["Список ингредиентов не может быть пустым."]}
            )

        ingredient_ids = [item['id'] for item in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise ValidationError(
                {"ingredients": ["Ингредиенты не должны повторяться."]}
            )

        return data

    def create_recipe_ingredients(self, recipe, ingredients_data):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        user = self.context['request'].user
        recipe = Recipe.objects.create(author=user, **validated_data)
        self.create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.create_recipe_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)


class ShortRecipeSerializer(slz.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(UserSerializer):
    recipes = slz.SerializerMethodField()
    recipes_count = slz.ReadOnlyField(source='recipes.count')

    class Meta(UserSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit') if request else None
        recipes = obj.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]

        return ShortRecipeSerializer(
            recipes, many=True, context=self.context
        ).data


class SubscriptionSerializer(slz.Serializer):
    following_id = slz.IntegerField()

    def validate_following_id(self, value):
        user = self.context['request'].user
        following_user = get_object_or_404(User, pk=value)

        if following_user == user:
            raise slz.ValidationError("Невозможно подписаться на себя")
        if Follow.objects.filter(user=user, following=following_user).exists():
            raise slz.ValidationError("Вы уже подписаны на этого пользователя")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        following_user = User.objects.get(pk=validated_data['following_id'])
        follow = Follow.objects.create(user=user, following=following_user)
        return follow

    def to_representation(self, instance):
        return FollowSerializer(instance.following, context=self.context).data


class FavoriteSerializer(BaseUserRecipeSerializer):
    class Meta(BaseUserRecipeSerializer.Meta):
        model = Favorite


class ShoppingCartSerializer(BaseUserRecipeSerializer):
    class Meta(BaseUserRecipeSerializer.Meta):
        model = ShoppingCart