from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    first_name = models.CharField(
        max_length=16,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=16,
        verbose_name='Фамилия'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Электронная почта',
        error_messages={
            'unique': 'Пользователь с этой почтой уже зарегистрирован.',
        }
    )
    avatar = models.ImageField(
        upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='follower',
    )
    following = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='following',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_user_following',
            )
        ]

    def __str__(self):
        return f'Пользователь {self.user} подписчик автора - {self.following}'
