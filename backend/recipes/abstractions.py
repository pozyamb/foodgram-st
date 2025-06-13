from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class UserRecipe(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        'Recipe',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(class)s_unique',
            )
        ]

    def __str__(self):
        return f'{self.user} добавил {self.recipe}'