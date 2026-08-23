from sqlalchemy import create_engine, MetaData, select, text
from app.config import settings


SQLITE_URL = "sqlite:///./hospital.db"
TARGET_URL = settings.DATABASE_URL

source_engine = create_engine(SQLITE_URL)
target_engine = create_engine(TARGET_URL, pool_pre_ping=True)

source_metadata = MetaData()
target_metadata = MetaData()

source_metadata.reflect(bind=source_engine)
target_metadata.reflect(bind=target_engine)


TABLE_ORDER = [
    "users",
    "doctors",
    "working_hours",
    "doctor_leaves",
    "appointments",
    "prescriptions",
    "notifications",
    "calendar_events",
]


def main():
    print("========================================")
    print("SQLite → Supabase migration")
    print("========================================")

    with source_engine.connect() as source, target_engine.begin() as target:

        # Prevent accidental duplicate migration
        for table_name in TABLE_ORDER:
            target_table = target_metadata.tables[table_name]
            existing = target.execute(
                select(target_table).limit(1)
            ).first()

            if existing:
                raise RuntimeError(
                    f"Supabase table '{table_name}' already contains data. "
                    "Migration stopped."
                )

        for table_name in TABLE_ORDER:
            source_table = source_metadata.tables[table_name]
            target_table = target_metadata.tables[table_name]

            source_columns = set(source_table.columns.keys())

            rows = source.execute(
                select(source_table)
            ).mappings().all()

            print(f"\nMigrating {table_name}: {len(rows)} rows")

            if not rows:
                continue

            data = []

            for row in rows:
                record = {}

                for column in target_table.columns:
                    name = column.name

                    if name in source_columns:
                        record[name] = row[name]

                    elif name == "is_active":
                        # New field added after old SQLite DB was created
                        record[name] = True

                    elif column.default is not None:
                        # Let SQLAlchemy/PostgreSQL use its default
                        continue

                    elif column.server_default is not None:
                        continue

                    elif column.nullable:
                        record[name] = None

                data.append(record)

            if data:
                target.execute(target_table.insert(), data)

        # Reset common integer PK sequences
        print("\nResetting PostgreSQL sequences...")

        for table_name in TABLE_ORDER:
            target_table = target_metadata.tables[table_name]

            if "id" not in target_table.columns:
                continue

            max_id = target.execute(
                select(target_table.c.id)
                .order_by(target_table.c.id.desc())
                .limit(1)
            ).scalar_one_or_none()

            if max_id is None:
                continue

            sequence_name = target.execute(
                text(
                    "SELECT pg_get_serial_sequence(:table_name, 'id')"
                ),
                {
                    "table_name": f"public.{table_name}"
                }
            ).scalar_one_or_none()

            if sequence_name:
                target.execute(
                    text(
                        "SELECT setval(:sequence_name, :value, true)"
                    ),
                    {
                        "sequence_name": sequence_name,
                        "value": int(max_id),
                    }
                )

    print("\n========================================")
    print("MIGRATION COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()