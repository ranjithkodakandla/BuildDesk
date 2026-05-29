from sqlalchemy import create_engine, text
engine = create_engine("postgresql+psycopg://builddesk_user:BuildDesk\!2024SQL@localhost:5432/builddesk")
with engine.connect() as conn:
    conn.execute(text("INSERT INTO tenants (id, name, created_at) VALUES ('11111111-1111-1111-1111-111111111111', 'Test Tenant', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING;"))
    conn.execute(text("INSERT INTO projects (id, tenant_id, name, created_at) VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'Test Project', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING;"))
    conn.commit()
    print("Seeded successfully")
