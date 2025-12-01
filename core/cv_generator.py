from llama_cpp import Llama
from core.cv_formatter import build_candidate_details

MODEL_PATH = "./gemma-3-12b-it-Q4_K_M.gguf"

llm = Llama(
    model_path=MODEL_PATH,
    n_gpu_layers=-1,
    n_ctx=8192,
    verbose=False
)

from core.prompt import system_instruction


def generate_cv(profile: dict, extra_instructions: str = "Tone: professional, one-page.") -> str:
    """
    Uses YOUR original prompt exactly as-is.
    """

    candidate_details = build_candidate_details(profile)

    user_prompt = f"""### Candidate details / Job target:
{candidate_details}

### Additional instructions:
{extra_instructions}
"""

    prompt = f"""<start_of_turn>user
{system_instruction}

{user_prompt}
<end_of_turn>
<start_of_turn>model
"""

    output = llm(
        prompt,
        max_tokens=1200,
        temperature=0.7,
        top_p=0.9,
        stop=["<end_of_turn>"],
        echo=False
    )

    return output["choices"][0]["text"].strip()
