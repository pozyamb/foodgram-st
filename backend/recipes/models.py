from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from recipes.abstractions import UserRecipe

User = get_user_model()


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=64,
        unique=True,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=16,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(1)
        ]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        ordering = ['recipe']
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} '
            f'- {self.amount} {self.ingredient.measurement_unit}'
        )


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField(
        verbose_name='Название',
        max_length=64,
    )
    text = models.TextField(
        verbose_name='Описание',
    )
    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='recipes/',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through=RecipeIngredient,
        verbose_name='Ингредиенты',
        related_name='recipes',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления (минуты)',
        validators=[MinValueValidator(2)],
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        default=timezone.now,
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def __str__(self):
        return self.name


class Favorite(UserRecipe):

    class Meta(UserRecipe.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        default_related_name = 'favorites'

    def __str__(self):
        return f'Пользователь {self.user} добавил в избранное {self.recipe}'


class ShoppingCart(UserRecipe):

    class Meta(UserRecipe.Meta):
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_carts'

    def __str__(self):
        return f'Пользователь {self.user} добавил в список покупок {self.recipe}'
