from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.io import DropdownInput, IntInput
import standard_langflow


class StandardResponses(LCModelComponent):
    display_name = "Standard Responses"
    name = "StandardResponses"
    icon = "Snowflake"
    description = "Private native Responses (/responses/v1) via LLM_PROXY_STANDARD. store=false, ordered-items streaming & encrypted reasoning preserved."
    inputs = [
        *LCModelComponent.get_base_inputs(),
        DropdownInput(
            name="model_id",
            display_name="Published model",
            options=[],
            refresh_button=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="reasoning_effort",
            display_name="Explicit reasoning effort",
            options=["unspecified", "low", "medium", "high"],
            value="unspecified",
            advanced=True,
        ),
        IntInput(name="max_tokens", display_name="Output tokens", value=2048, advanced=True),
    ]

    def _remediate_model_error(self, *args):
        return False

    def update_build_config(self, build_config, field_value, field_name=None):
        return standard_langflow.refresh(build_config, "responses")

    def build_model(self) -> LanguageModel:
        return standard_langflow.build(
            "responses",
            self.model_id,
            self.stream,
            max_tokens=self.max_tokens,
            reasoning_effort=getattr(self, "reasoning_effort", "unspecified"),
        )
