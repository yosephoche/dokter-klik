"""Management command to import ICD-10 codes from a CSV file.

Usage:
    python manage.py import_icd10 --file /path/to/icd10.csv

CSV format expected (header row):
    code,description_en,description_id,chapter,block,category,is_billable

Example CSV sources:
    - WHO ICD-10 public dataset
    - Indonesian Kemenkes ICD-10 dataset
"""
import csv
import sys
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.emr.models import ICD10Code


class Command(BaseCommand):
    help = 'Import ICD-10 codes from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', type=str,
            help='Path to ICD-10 CSV file',
            default=None
        )
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Bulk insert batch size (default: 500)'
        )

    def handle(self, *args, **options):
        file_path = options.get('file')

        if not file_path:
            # Try default locations
            for default in ['data/icd10.csv', 'icd10.csv']:
                if Path(default).exists():
                    file_path = default
                    break

        if not file_path or not Path(file_path).exists():
            raise CommandError(
                f'ICD-10 CSV file not found. Provide --file or place icd10.csv in project root.\n'
                f'Download from: https://icd.who.int/browse10/Content/statichtml/ICD10Volume2_en_2019.pdf'
            )

        self.stdout.write(f'Importing ICD-10 codes from {file_path}...')
        batch = []
        count = 0
        existing_codes = set(ICD10Code.objects.values_list('code', flat=True))

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('code', '').strip().upper()
                if not code or code in existing_codes:
                    continue
                batch.append(ICD10Code(
                    code=code,
                    description_en=row.get('description_en', '').strip()[:500],
                    description_id=row.get('description_id', '').strip()[:500],
                    chapter=row.get('chapter', '').strip()[:10],
                    block=row.get('block', '').strip()[:20],
                    category=row.get('category', '').strip()[:10],
                    is_billable=row.get('is_billable', '1').strip() not in ('0', 'false', 'False'),
                ))
                existing_codes.add(code)

                if len(batch) >= options['batch_size']:
                    ICD10Code.objects.bulk_create(batch, ignore_conflicts=True)
                    count += len(batch)
                    batch = []
                    self.stdout.write(f'  Imported {count} codes...', ending='\r')
                    sys.stdout.flush()

        if batch:
            ICD10Code.objects.bulk_create(batch, ignore_conflicts=True)
            count += len(batch)

        total = ICD10Code.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nImport complete. Added {count} codes. Total in DB: {total}'
        ))
