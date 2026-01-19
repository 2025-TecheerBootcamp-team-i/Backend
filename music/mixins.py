"""
Model Mixins

재사용 가능한 모델 기능을 제공하는 Mixin 클래스들입니다.
"""
from django.db import models
from django.utils import timezone


class TimestampMixin(models.Model):
    """
    생성/수정 시각을 자동으로 관리하는 Mixin
    
    사용 예시:
        class Music(TimestampMixin):
            # created_at, updated_at 필드가 자동으로 추가됨
            pass
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시각")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정 시각")
    
    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Soft Delete 기능을 제공하는 Mixin
    
    is_deleted 필드를 추가하고 delete() 메서드를 오버라이드합니다.
    
    사용 예시:
        from .managers import SoftDeleteManager
        
        class Music(SoftDeleteMixin, TimestampMixin):
            # ... fields ...
            
            objects = SoftDeleteManager()
            all_objects = models.Manager()
    """
    is_deleted = models.BooleanField(default=False, verbose_name="삭제 여부")
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Soft Delete 수행 (is_deleted=True로 업데이트)
        
        Args:
            using: 데이터베이스 별칭
            keep_parents: 부모 모델 유지 여부
            hard: True인 경우 하드 삭제 수행
        """
        if hard:
            # 하드 삭제: 실제 DB에서 삭제
            return super().delete(using=using, keep_parents=keep_parents)
        else:
            # 소프트 삭제: is_deleted=True로 업데이트
            self.is_deleted = True
            if hasattr(self, 'updated_at'):
                self.updated_at = timezone.now()
            self.save(using=using)
    
    def restore(self, using=None):
        """
        삭제된 레코드 복구 (is_deleted=False로 업데이트)
        
        Args:
            using: 데이터베이스 별칭
        """
        self.is_deleted = False
        if hasattr(self, 'updated_at'):
            self.updated_at = timezone.now()
        self.save(using=using)
    
    def hard_delete(self, using=None, keep_parents=False):
        """
        하드 삭제 수행 (실제 데이터베이스에서 삭제)
        
        Warning:
            이 메서드는 실제로 데이터를 삭제합니다. 주의해서 사용하세요.
        """
        return super().delete(using=using, keep_parents=keep_parents)


class TrackableMixin(TimestampMixin, SoftDeleteMixin):
    """
    Timestamp + Soft Delete 기능을 함께 제공하는 Mixin
    
    대부분의 모델에서 사용할 수 있는 완전한 기능을 제공합니다.
    
    사용 예시:
        from .managers import SoftDeleteManager
        
        class Music(TrackableMixin):
            # ... fields ...
            
            objects = SoftDeleteManager()
            all_objects = models.Manager()
    """
    
    class Meta:
        abstract = True
