from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from tableno_mcp.config import CHARACTERS_WRITE, MAX_CONFIRMATION_TOKEN_LENGTH, SESSIONS_WRITE
from tableno_mcp.creation import confirm_creation, preview_creation

Edition = Literal["6th", "7th"]
Identifier = Annotated[int, Field(gt=0, lt=2**63)]
Ability = Annotated[int, Field(ge=1, le=999)]
SkillPoints = Annotated[int, Field(ge=0, le=999)]
ConfirmationToken = Annotated[str, Field(min_length=1, max_length=MAX_CONFIRMATION_TOKEN_LENGTH)]


class CreationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionInput(CreationInput):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    date: Annotated[AwareDatetime | None, Field(description="開始日時。タイムゾーン付きのISO 8601で指定")] = None
    description: Annotated[str, Field(max_length=2000)] = ""
    location: Annotated[str, Field(max_length=200)] = ""
    group_id: Identifier | None = None
    scenario_id: Identifier | None = None
    visibility: Literal["private", "group", "link", "public"] | None = None
    duration_minutes: Annotated[int, Field(ge=0, le=2**31 - 1)] = 0
    coc_edition: Edition = "6th"
    as_gm: bool = False
    send_discord_notification: bool = False
    sync_google_calendar: bool = False


class Abilities(CreationInput):
    str: Ability
    con: Ability
    pow: Ability
    dex: Ability
    app: Ability
    siz: Ability
    int: Ability
    edu: Ability


class SkillInput(CreationInput):
    skill_name: Annotated[str, Field(min_length=1, max_length=100)]
    base_value: SkillPoints = 0
    occupation_points: SkillPoints = 0
    interest_points: SkillPoints = 0
    other_points: SkillPoints = 0


class EquipmentInput(CreationInput):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    item_type: Literal["item", "weapon", "armor"] = "item"
    quantity: Annotated[int, Field(ge=1, le=2**31 - 1)] = 1
    skill_name: Annotated[str, Field(max_length=100)] = ""
    damage: Annotated[str, Field(max_length=20)] = ""
    description: Annotated[str, Field(max_length=500)] = ""


class CharacterInput(CreationInput):
    edition: Edition
    name: Annotated[str, Field(min_length=1, max_length=100)]
    abilities: Abilities
    name_kana: Annotated[str, Field(max_length=100)] = ""
    occupation: Annotated[str, Field(max_length=100)] = ""
    occupation_point_method: Annotated[str, Field(max_length=20)] = ""
    age: Annotated[int | None, Field(ge=15, le=90)] = None
    luck: Annotated[int | None, Field(description="7版では必須。15～90の5刻み")] = None
    skills: Annotated[list[SkillInput], Field(max_length=100)] = Field(default_factory=list)
    equipment: Annotated[list[EquipmentInput], Field(max_length=50)] = Field(default_factory=list)


def add_creation_tools(server, read, write):
    preview = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

    @server.tool(annotations=preview)
    async def preview_session_creation(session: SessionInput) -> dict[str, Any]:
        """卓の作成内容、公開範囲、Discord通知とGoogleカレンダー同期の予定を確認します。"""
        return await read(preview_creation, SESSIONS_WRITE, kind="session", payload=session.model_dump(mode="json"))

    @server.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
    )
    async def create_session(confirmation_token: ConfirmationToken) -> dict[str, Any]:
        """プレビューを本人に提示し、保存の承諾を受けてから卓を作成します。卓の詳細URLを返します。"""
        return await write(confirm_creation, SESSIONS_WRITE, kind="session", confirmation_token=confirmation_token)

    @server.tool(annotations=preview)
    async def preview_character_creation(character: CharacterInput) -> dict[str, Any]:
        """CoC 6版・7版の探索者シートの作成内容を確認します。"""
        return await read(
            preview_creation, CHARACTERS_WRITE, kind="character", payload=character.model_dump(mode="json")
        )

    @server.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    )
    async def create_character(confirmation_token: ConfirmationToken) -> dict[str, Any]:
        """プレビューを本人に提示し、保存の承諾を受けてから探索者を作成します。詳細URLを返します。"""
        return await write(confirm_creation, CHARACTERS_WRITE, kind="character", confirmation_token=confirmation_token)
