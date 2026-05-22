import asyncio

from app.core.database import SessionLocal
from app.schemas import ApiKeyCreate, DashboardCreate, EventIn, SavedQueryCreate, SignupRequest, WidgetCreate
from app.services import ApiKeyService, AuthService, DashboardService, IngestionService


async def main() -> None:
    async with SessionLocal() as session:
        auth = AuthService(session)
        user, _ = await auth.signup(
            SignupRequest(
                organization_name="Wexa Demo",
                organization_slug="wexa-demo",
                full_name="Demo Owner",
                email="owner@wexa.example",
                password="ChangeMe123!",
            )
        )
        key, raw_key = await ApiKeyService(session).create(user, ApiKeyCreate(name="Demo ingest key"))
        ingestion = IngestionService(session)
        for event_type in ["page_view", "signup", "purchase", "error"]:
            await ingestion.ingest_one(
                user.organization_id,
                EventIn(event_type=event_type, properties={"source": "seed", "value": 1}),
                key,
            )
        dashboard_service = DashboardService(session)
        query = await dashboard_service.create_query(
            user.organization_id, SavedQueryCreate(name="All events", event_type=None)
        )
        dashboard = await dashboard_service.create_dashboard(
            user, DashboardCreate(name="Executive Overview", visibility="team", auto_refresh_seconds=60)
        )
        await dashboard_service.add_widget(
            user.organization_id,
            dashboard.id,
            WidgetCreate(title="Event Volume", type="line", saved_query_id=query.id),
        )
        print(f"Seed complete. Demo API key: {raw_key}")


if __name__ == "__main__":
    asyncio.run(main())

