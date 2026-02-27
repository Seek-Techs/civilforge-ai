import json
import logging

from dotenv import load_dotenv
from django.conf import settings
from langchain_experimental.utilities import PythonREPL
from pydantic import BaseModel, Field, ValidationError
from typing import List
from langchain_core.output_parsers import PydanticOutputParser
from langchain_ollama import ChatOllama
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from .models import Project
from django_ratelimit.decorators import ratelimit
from django.utils import timezone
from langchain_community.tools import DuckDuckGoSearchRun
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

load_dotenv()
logger = logging.getLogger(__name__)
repl = PythonREPL()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class BOQItem(BaseModel):
    item: str = Field(..., description="Name of the item")
    quantity: float = Field(..., description="Quantity")
    unit: str = Field(..., description="Unit of measurement")
    unit_rate_naira: float = Field(..., description="Rate per unit in Naira")
    total_naira: float = Field(..., description="Total cost in Naira")

class BOQOutput(BaseModel):
    items: List[BOQItem]
    grand_total_naira: float
    contingency_percent: float = Field(..., ge=5, le=30)
    risks: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)

parser = PydanticOutputParser(pydantic_object=BOQOutput)


# ── Helper: check Ollama is reachable ────────────────────────────────────────

def _check_ollama():
    """Return (ok: bool, message: str)."""
    import urllib.request
    import urllib.error
    base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
    try:
        urllib.request.urlopen(f"{base_url}/api/tags", timeout=3)
        return True, ""
    except urllib.error.URLError:
        return False, (
            "Ollama service is not running. "
            "Please start it with `ollama serve` and ensure the model is pulled."
        )


# ── Project CRUD views ────────────────────────────────────────────────────────

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ['name', 'description', 'status', 'location', 'notes']
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:my_projects')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'Create New Project'
        ctx['submit_label'] = 'Create Project'
        return ctx

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, f'Project "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ['name', 'description', 'status', 'location', 'notes']
    template_name = 'projects/project_form.html'

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'Edit Project: {self.object.name}'
        ctx['submit_label'] = 'Save Changes'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Project updated successfully.')
        return super().form_valid(form)


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == 'POST':
        name = project.name
        project.delete()
        messages.success(request, f'Project "{name}" deleted.')
        return redirect('projects:my_projects')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@login_required
def my_projects(request):
    my_projects_qs = Project.objects.filter(owner=request.user).order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        my_projects_qs = my_projects_qs.filter(status=status_filter)

    # Stats for dashboard
    all_projects = Project.objects.filter(owner=request.user)
    stats = {
        'total': all_projects.count(),
        'active': all_projects.filter(status='active').count(),
        'planning': all_projects.filter(status='planning').count(),
        'completed': all_projects.filter(status='completed').count(),
        'with_boq': all_projects.exclude(boq_result=None).count(),
    }

    return render(request, 'projects/my_projects.html', {
        'projects': my_projects_qs,
        'stats': stats,
        'status_filter': status_filter,
        'status_choices': Project.STATUS_CHOICES,
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    return render(request, 'projects/project_detail.html', {'project': project})


# ── BOQ analysis ─────────────────────────────────────────────────────────────

@ratelimit(key='user', rate='5/m', method='POST', block=True)
@require_POST
@login_required
def analyze_boq(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)

    if not project.description.strip():
        return JsonResponse({"success": False, "error": "Project description is empty. Please add a description before generating a BOQ."}, status=400)

    # Check Ollama health first
    ok, err_msg = _check_ollama()
    if not ok:
        return JsonResponse({"success": False, "error": err_msg}, status=503)

    model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3.1:8b')
    llm = ChatOllama(
        model=model_name,
        temperature=0.2,
        max_tokens=1200,
        timeout=120,
    )

    # Fetch real prices
    search = DuckDuckGoSearchRun()
    materials = ["12mm rebar", "cement 50kg bag", "ready mix concrete m3"]
    price_info = ""
    for mat in materials:
        try:
            result = search.run(f"current price {mat} Lagos Nigeria Naira 2026")
            price_info += f"{mat}: {result}\n"
        except Exception as e:
            logger.warning(f"Price lookup failed for {mat}: {e}")
            price_info += f"{mat}: price lookup unavailable\n"

    base_prompt = f"""You are a senior Quantity Surveyor in Lagos, Nigeria (2026).
Project description: {project.description}
Location: {project.location or 'Lagos, Nigeria'}

Use these current market prices (approximate):
{price_info}

This may be a small element — do NOT assume a full building unless described.
For example, a 3m beam has concrete volume ~0.3–0.5 m³, rebar ~5–20 kg.

Generate a realistic, detailed BOQ summary.
Return **ONLY** valid JSON matching this exact schema — no markdown, no code fences, no explanation.
{parser.get_format_instructions()}

Ensure: quantity × unit_rate_naira = total_naira for each item.
Ensure grand_total_naira = sum of all total_naira values."""

    raw_output = ""
    parsed = None

    def _parse_attempt(prompt):
        nonlocal raw_output
        response = llm.invoke(prompt)
        raw_output = response.content.strip()
        # Strip any markdown fences the model may have added despite instructions
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        logger.debug(f"Raw LLM output: {raw_output[:500]}")
        return parser.parse(raw_output)

    try:
        parsed = _parse_attempt(base_prompt)
    except (ValidationError, json.JSONDecodeError) as e1:
        logger.warning(f"Parse attempt 1 failed: {e1}")
        retry_prompt = (
            base_prompt
            + "\n\nIMPORTANT: Your previous response failed to parse. "
            "Return ONLY raw JSON. Absolutely no markdown, no ```json, no explanations."
        )
        try:
            parsed = _parse_attempt(retry_prompt)
        except Exception as e2:
            logger.error(f"Parse attempt 2 failed: {e2} | Raw: {raw_output}")
            return JsonResponse({
                "success": False,
                "error": f"The AI model returned an unexpected format after two attempts. Please try again. (Detail: {str(e2)})"
            }, status=500)

    # Validate totals using Python REPL
    try:
        validation_code = "\n".join(
            f"item_{i}_total = {item.quantity} * {item.unit_rate_naira}"
            for i, item in enumerate(parsed.items)
        ) + "\ngrand = " + " + ".join(f"item_{i}_total" for i in range(len(parsed.items)))
        validated_grand = float(repl.run(validation_code + "\ngrand"))
        if abs(validated_grand - parsed.grand_total_naira) > parsed.grand_total_naira * 0.05:
            logger.warning(f"Total mismatch: computed={validated_grand}, model={parsed.grand_total_naira}. Correcting.")
            # Auto-correct the grand total
            boq_data = parsed.model_dump()
            boq_data['grand_total_naira'] = round(validated_grand, 2)
        else:
            boq_data = parsed.model_dump()
    except Exception as math_e:
        logger.warning(f"Math validation failed: {math_e}")
        boq_data = parsed.model_dump()

    # Save to DB
    project.boq_result = boq_data
    project.boq_generated_at = timezone.now()
    project.save(update_fields=['boq_result', 'boq_generated_at'])

    return JsonResponse({"success": True, "boq": boq_data})


@require_POST
@login_required
def clear_boq(request, pk):
    """Allow user to clear a saved BOQ result."""
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.boq_result = None
    project.boq_generated_at = None
    project.save(update_fields=['boq_result', 'boq_generated_at'])
    messages.success(request, 'BOQ cleared. You can generate a new one.')
    return redirect('projects:project_detail', pk=pk)
