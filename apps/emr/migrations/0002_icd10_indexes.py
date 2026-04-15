"""Migration: pg_trgm extension + GIN index for ICD-10 fast search."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('emr', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="-- cannot safely drop pg_trgm if other indexes use it",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS idx_icd10_search_gin "
                "ON emr_icd10code "
                "USING gin((description_en || ' ' || COALESCE(description_id, '')) gin_trgm_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS idx_icd10_search_gin;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS idx_icd10_code_prefix "
                "ON emr_icd10code(code varchar_pattern_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS idx_icd10_code_prefix;",
        ),
    ]
