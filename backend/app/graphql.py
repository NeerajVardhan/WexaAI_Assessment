import strawberry
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class PlatformSummary:
    name: str
    required_modules: list[str]
    optional_modules: list[str]


@strawberry.type
class Query:
    @strawberry.field
    def platform_summary(self) -> PlatformSummary:
        return PlatformSummary(
            name="WexaAI Analytics",
            required_modules=["auth", "ingestion", "dashboards", "api_keys"],
            optional_modules=["alerts", "reports", "realtime", "webhooks", "retention", "feature_flags"],
        )


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)

