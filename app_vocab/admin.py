# app_vocab/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Word, UserWord, UserProfile


# Регистрируем модель Word
@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    """
    Настройки для отображения модели Word в админ-панели.
    """
    list_display = ('original', 'transcription', 'translation', 'difficulty_level', 'date_added')
    search_fields = ('original', 'translation', 'transcription')
    list_filter = ('difficulty_level', 'date_added')
    fields = ('original', 'transcription', 'translation', 'example_sentence', 'difficulty_level')


# Регистрируем модель UserWord
@admin.register(UserWord)
class UserWordAdmin(admin.ModelAdmin):
    """
    Настройки для отображения прогресса пользователей.
    """
    list_display = ('user', 'word', 'repetition', 'interval', 'next_review', 'get_knowledge_level')
    search_fields = ('user__username', 'word__original', 'word__translation')
    list_filter = ('repetition', 'next_review')
    readonly_fields = ('last_reviewed', 'correct_answers', 'wrong_answers')

    def get_knowledge_level(self, obj):
        return obj.get_knowledge_level()

    get_knowledge_level.short_description = 'Уровень знания'


# Регистрируем модель UserProfile как inline для User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ('telegram_id', 'daily_review_limit', 'notification_enabled',
              'total_words_learned', 'total_reviews', 'streak_days')


# Расширяем стандартную админку User
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_telegram_id', 'get_words_count')

    def get_telegram_id(self, obj):
        if hasattr(obj, 'userprofile'):
            return obj.userprofile.telegram_id
        return None

    get_telegram_id.short_description = 'Telegram ID'

    def get_words_count(self, obj):
        return UserWord.objects.filter(user=obj).count()

    get_words_count.short_description = 'Количество слов'


# Перерегистрируем User с новой админкой
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
