from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.io import DropdownInput, IntInput
import standard_langflow


class StandardMessages(LCModelComponent):
    display_name = "Standard Messages"
    name = "StandardMessages"
    icon = "Snowflake"
    description = "Private native Anthropic Messages (/messages) via LLM_PROXY_STANDARD. Live catalog, optional extended thinking, retry0, no fallback."
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
            name="extended_thinking",
            display_name="Extended thinking",
            options=["disabled", "enabled"],
            value="disabled",
            advanced=True,
        ),
        IntInput(name="thinking_budget_tokens", display_name="Thinking budget tokens", value=2048, advanced=True),
        IntInput(name="max_tokens", display_name="Output tokens", value=2048, advanced=True),
    ]

    def _remediate_model_error(self, *args):
        return False

    def update_build_config(self, build_config, field_value, field_name=None):
        return standard_langflow.refresh(build_config, "messages")

    def build_model(self) -> LanguageModel:
        return standard_langflow.build(
            "messages",
            self.model_id,
            self.stream,
            max_tokens=self.max_tokens,
            extended_thinking=getattr(self, "extended_thinking", "disabled"),
            thinking_budget_tokens=getattr(self, "thinking_budget_tokens", 2048),
        )
