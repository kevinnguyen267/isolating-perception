"""VLM-as-planner with the physical constraints of the scene stated in the prompt."""

from functools import partial

from modes import planner

build_prompt = partial(planner.build_prompt, priors=True)
