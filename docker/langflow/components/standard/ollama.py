from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.io import DropdownInput, IntInput
import standard_langflow


class PrivateOllama(LCModelComponent):
    display_name = "Ollama Private Direct"
    name = "PrivateOllama"
    icon = "Ollama"
    description = "Direct private SPCS Ollama Chat API; live discovery, retry0, no fallback."
    inputs = [
        *LCModelComponent.get_base_inputs(),
        DropdownInput(
            name="model_id",
            display_name="Ollama model",
            options=[],
            refresh_button=True,
            real_time_refresh=True,
        ),
        IntInput(name="max_tokens", display_name="Output tokens", value=2048, advanced=True),
    ]

    def _remediate_model_error(self, *args):
        return False

    def update_build_config(self, build_config, field_value, field_name=None):
        return standard_langflow.refresh(build_config, "ollama")

    def build_model(self) -> LanguageModel:
        return standard_langflow.build("ollama", self.model_id, self.stream, max_tokens=self.max_tokens)
