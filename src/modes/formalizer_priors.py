"""VLM-as-formalizer with the physical constraints of the scene stated in the prompt."""

from functools import partial

from modes import formalizer

build_grounded_prompt = partial(formalizer.build_grounded_prompt, priors=True)
