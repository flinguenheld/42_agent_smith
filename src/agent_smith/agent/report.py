from agent_smith.agent.prompt import SYSTEM_PROMPT
from agent_smith.data import BENCHMARK
from agent_smith.llm.client import LLMResponse
from agent_smith.models import SolutionOutput, StepMetrics


class Report:
    """Collect the StepMetrics of one task and build its SolutionOutput."""

    def __init__(
        self,
        api_url: str,
        model_name: str,
        benchmark: str = BENCHMARK,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.api_url = api_url
        self.model_name = model_name
        self.benchmark = benchmark
        self.system_prompt = system_prompt
        self.steps: list[StepMetrics] = []

    # ----------------------------------------------------------- ADD STEP ----
    def add_step(
        self, response: LLMResponse, code: str, observation: str
    ) -> StepMetrics:
        """Save and return the metrics of one step ("" if nothing ran)."""

        step = StepMetrics(
            step=len(self.steps) + 1,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            request_time_ms=response.request_time_ms,
            api_url=self.api_url,
            model_name=self.model_name,
            llm_output=response.text,
            sandbox_input=code,
            sandbox_output=observation,
            retries=response.retries,
        )
        self.steps.append(step)
        return step

    # -------------------------------------------------------------- BUILD ----
    def build(
        self,
        task_id: int,
        answer: str | None,
        error: str | None,
        seconds: float,
    ) -> SolutionOutput:
        """Gather the steps and their totals into the subject's model."""

        return SolutionOutput(
            task_id=str(task_id),
            benchmark=self.benchmark,
            success=answer is not None,
            solution=answer or "",
            iterations=len(self.steps),
            total_requests=sum(s.retries + 1 for s in self.steps),
            total_input_tokens=sum(s.input_tokens for s in self.steps),
            total_output_tokens=sum(s.output_tokens for s in self.steps),
            total_time_seconds=seconds,
            steps=self.steps,
            system_prompt=self.system_prompt,
            error=error,
        )
