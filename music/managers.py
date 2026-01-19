"""
Custom Model Managers

Django 모델의 기본 쿼리셋을 커스터마이징하는 매니저 클래스들입니다.
"""
from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """
    Soft Delete를 지원하는 QuerySet
    
    is_deleted 필드를 자동으로 필터링합니다.
    """
    
    def active(self):
        """
        삭제되지 않은 레코드만 반환
        
        Returns:
            is_deleted가 False 또는 None인 레코드
        """
        return self.filter(is_deleted__in=[False, None])
    
    def deleted(self):
        """
        삭제된 레코드만 반환
        
        Returns:
            is_deleted가 True인 레코드
        """
        return self.filter(is_deleted=True)
    
    def delete(self):
        """
        소프트 삭제 수행 (is_deleted=True로 업데이트)
        
        실제 데이터베이스에서 삭제하지 않고 is_deleted 플래그만 True로 설정합니다.
        """
        from django.utils import timezone
        return self.update(is_deleted=True, updated_at=timezone.now())
    
    def hard_delete(self):
        """
        하드 삭제 수행 (실제 데이터베이스에서 삭제)
        
        Warning:
            이 메서드는 실제로 데이터를 삭제합니다. 주의해서 사용하세요.
        """
        return super().delete()


class SoftDeleteManager(models.Manager):
    """
    Soft Delete를 지원하는 Model Manager
    
    기본적으로 삭제되지 않은 레코드만 조회합니다.
    
    사용 예시:
        class Music(models.Model):
            # ... fields ...
            is_deleted = models.BooleanField(default=False)
            
            objects = SoftDeleteManager()  # 기본 매니저
            all_objects = models.Manager()  # 모든 레코드 (삭제된 것 포함)
        
        # 삭제되지 않은 음악만 조회
        Music.objects.all()
        
        # 삭제된 음악 포함 모든 음악 조회
        Music.all_objects.all()
        
        # 소프트 삭제
        music = Music.objects.get(id=1)
        music.delete()  # is_deleted=True로 업데이트
        
        # 하드 삭제
        music = Music.all_objects.get(id=1)
        music.hard_delete()  # 실제 DB에서 삭제
    """
    
    def get_queryset(self):
        """
        기본 QuerySet 반환
        
        is_deleted가 False 또는 None인 레코드만 반환합니다.
        """
        return SoftDeleteQuerySet(self.model, using=self._db).active()
    
    def deleted(self):
        """
        삭제된 레코드 조회
        
        Returns:
            is_deleted가 True인 레코드
        """
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()
    
    def all_with_deleted(self):
        """
        삭제 여부와 관계없이 모든 레코드 조회
        
        Returns:
            모든 레코드 (삭제된 것 포함)
        """
        return SoftDeleteQuerySet(self.model, using=self._db)


class ActiveObjectsManager(models.Manager):
    """
    삭제되지 않은 레코드만 조회하는 매니저 (SoftDeleteManager의 별칭)
    
    더 직관적인 이름을 원하는 경우 사용할 수 있습니다.
    
    사용 예시:
        class Music(models.Model):
            # ... fields ...
            is_deleted = models.BooleanField(default=False)
            
            active_objects = ActiveObjectsManager()  # 활성 레코드만
            objects = models.Manager()  # 모든 레코드 (기본)
    """
    
    def get_queryset(self):
        """삭제되지 않은 레코드만 반환"""
        return super().get_queryset().filter(is_deleted__in=[False, None])
