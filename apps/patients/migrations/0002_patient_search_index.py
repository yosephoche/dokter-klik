"""Migration: GIN trigram index on patients name_search column for fast ILIKE queries."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS idx_patient_name_search_gin "
                "ON patients_patient "
                "USING gin(name_search gin_trgm_ops);"
            ),
            reverse_sql="DROP INDEX IF EXISTS idx_patient_name_search_gin;",
        ),
    ]
