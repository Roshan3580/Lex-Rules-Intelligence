import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Clock,
  ExternalLink,
  FileText,
  Loader2,
  Plus,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  api,
  CaseWorkflow,
  StateOut,
  TAX_TYPES,
  TaxType,
  WorkflowStep,
  WorkflowTemplate,
  taxTypeLabel,
} from "@/lib/api";

const ANY = "__any__";

const stageBadgeClass = (status?: string | null) => {
  if (status === "complete") return "bg-success/10 text-success";
  if (status === "active") return "bg-primary/10 text-primary";
  return "bg-secondary text-muted-foreground";
};

const StepIcon = ({ status }: { status?: string | null }) => {
  if (status === "complete")
    return <CheckCircle2 className="h-4 w-4 text-success" />;
  if (status === "active")
    return <Clock className="h-4 w-4 text-primary" />;
  return <Circle className="h-4 w-4 text-muted-foreground" />;
};

const Workflows = () => {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [cases, setCases] = useState<CaseWorkflow[]>([]);
  const [activeCase, setActiveCase] = useState<CaseWorkflow | null>(null);
  const [states, setStates] = useState<StateOut[]>([]);
  const [filterState, setFilterState] = useState<string>("");
  const [filterTax, setFilterTax] = useState<TaxType | "">("");
  const [newTitle, setNewTitle] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [creating, setCreating] = useState<boolean>(false);
  const [stepBusy, setStepBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ---- initial load ----
  useEffect(() => {
    api.states().then(setStates).catch(() => setStates([]));
  }, []);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [tpls, cs] = await Promise.all([
        api.workflowTemplates({
          state: filterState || undefined,
          tax_category: filterTax || undefined,
        }),
        api.listCases({}),
      ]);
      setTemplates(tpls);
      setCases(cs);
      if (!activeCase && cs.length) {
        const detail = await api.getCase(cs[0].id);
        setActiveCase(detail);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterState, filterTax]);

  const previewTemplate = templates[0];

  const previewSteps: WorkflowStep[] = useMemo(() => {
    if (activeCase) return activeCase.steps;
    if (previewTemplate) return previewTemplate.steps;
    return [];
  }, [activeCase, previewTemplate]);

  const completedCount = activeCase
    ? activeCase.completed_count
    : previewSteps.filter((s) => s.status === "complete").length;
  const totalCount = previewSteps.length;
  const progressPct = totalCount
    ? Math.round((completedCount / totalCount) * 100)
    : 0;

  const handleCreateCase = async () => {
    setCreating(true);
    setError(null);
    try {
      const c = await api.createCase({
        state: filterState || undefined,
        tax_category: filterTax || undefined,
        title: newTitle || undefined,
      });
      setNewTitle("");
      setCases((prev) => [c, ...prev]);
      setActiveCase(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  };

  const selectCase = async (id: string) => {
    setError(null);
    try {
      const detail = await api.getCase(id);
      setActiveCase(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const toggleStep = async (step: WorkflowStep) => {
    if (!activeCase) return;
    const isComplete = step.status === "complete";
    setStepBusy(step.key);
    setError(null);
    try {
      const updated = await api.updateCaseStep(activeCase.id, {
        step_key: step.key,
        completed: !isComplete,
      });
      setActiveCase(updated);
      setCases((prev) =>
        prev.map((c) =>
          c.id === updated.id
            ? {
                ...c,
                status: updated.status,
                completed_count: updated.completed_count,
                progress: updated.progress,
                current_stage: updated.current_stage,
              }
            : c,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStepBusy(null);
    }
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="app-label">
            Workflow guidance
          </p>
          <h1 className="font-serif text-3xl leading-tight tracking-tight mt-1">
            Tax filing workflows
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Source-grounded checklists derived from the indexed rule corpus —
            no mock data.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadAll()}
            disabled={loading}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* ---- Filters + new case ---- */}
      <div className="rounded-2xl glass p-6 space-y-4">
        <div className="grid md:grid-cols-4 gap-3">
          <div>
            <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">
              State
            </Label>
            <Select
              value={filterState || ANY}
              onValueChange={(v) => setFilterState(v === ANY ? "" : v)}
            >
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Any state" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any state</SelectItem>
                {states.map((s) => (
                  <SelectItem key={s.abbreviation} value={s.name}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Tax category
            </Label>
            <Select
              value={filterTax || ANY}
              onValueChange={(v) => setFilterTax(v === ANY ? "" : (v as TaxType))}
            >
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Any category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any category</SelectItem>
                {TAX_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="md:col-span-2">
            <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">
              New case title (optional)
            </Label>
            <div className="flex gap-2 mt-1">
              <Input
                placeholder="e.g. Q4 California sales tax filing"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
              />
              <Button
                onClick={() => void handleCreateCase()}
                disabled={creating}
                variant="hero"
              >
                {creating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4 mr-1" />
                )}
                Start case
              </Button>
            </div>
          </div>
        </div>

        {error && (
          <div className="text-xs text-destructive flex items-center gap-1.5">
            <AlertCircle className="h-3.5 w-3.5" /> {error}
          </div>
        )}
        {!loading && templates.length === 0 && (
          <p className="text-xs text-muted-foreground">
            No workflow templates available yet. Default templates are seeded
            on backend startup.
          </p>
        )}
        {!loading && previewTemplate && previewSteps.every((s) => (s.rule_count ?? s.rules.length) === 0) && (
          <p className="text-xs text-warning">
            ⚠ No published rules currently match these filters — checklists
            will use template defaults until you ingest and approve sources.
          </p>
        )}
      </div>

      {/* ---- Case list ---- */}
      <div className="grid md:grid-cols-[280px_1fr] gap-4">
        <div className="rounded-2xl glass p-4 space-y-2 max-h-[680px] overflow-auto">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">
            Active cases ({cases.length})
          </p>
          {cases.length === 0 && (
            <p className="text-xs text-muted-foreground">
              No cases yet. Start one with the form above.
            </p>
          )}
          {cases.map((c) => {
            const isActive = activeCase?.id === c.id;
            return (
              <button
                key={c.id}
                onClick={() => void selectCase(c.id)}
                className={`w-full text-left rounded-lg p-3 border transition-all ${
                  isActive
                    ? "border-primary/50 bg-primary/5"
                    : "border-border/50 hover:bg-secondary/50"
                }`}
              >
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono">
                  {c.case_id}
                </p>
                <p className="text-sm font-semibold mt-0.5 truncate">
                  {c.title || "Filing case"}
                </p>
                <div className="text-[11px] text-muted-foreground mt-1 flex items-center gap-2">
                  <span>{c.state || "—"}</span>
                  <span>·</span>
                  <span>{taxTypeLabel(c.tax_category)}</span>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-gradient-primary"
                    style={{ width: `${Math.round(c.progress * 100)}%` }}
                  />
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  {c.completed_count}/{c.step_count} ·{" "}
                  <span className={c.status === "completed" ? "text-success" : ""}>
                    {c.status}
                  </span>
                </p>
              </button>
            );
          })}
        </div>

        {/* ---- Active case / preview ---- */}
        <div className="space-y-4">
          <div className="rounded-2xl glass p-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                  {activeCase ? `Case · ${activeCase.case_id}` : "Workflow preview"}
                </p>
                <p className="text-2xl font-bold mt-1">
                  {activeCase
                    ? activeCase.title || "Filing case"
                    : previewTemplate?.title || "State tax filing workflow"}
                </p>
                {activeCase ? (
                  <p className="text-xs text-muted-foreground mt-1">
                    {activeCase.state || "any state"} ·{" "}
                    {taxTypeLabel(activeCase.tax_category)} · status{" "}
                    <span className="font-semibold">{activeCase.status}</span>
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground mt-1">
                    Live preview from indexed rules. Start a case to track
                    progress.
                  </p>
                )}
              </div>
              <span className="text-3xl font-bold gradient-text font-mono">
                {progressPct}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full bg-gradient-primary rounded-full transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {completedCount} of {totalCount} steps complete
            </p>
          </div>

          <div className="space-y-3">
            {previewSteps.map((step, i) => {
              const isComplete = step.status === "complete";
              const isCurrent =
                activeCase?.current_stage === step.key && !isComplete;
              const ruleCount = step.rule_count ?? step.rules.length;
              return (
                <div
                  key={step.key}
                  className={`rounded-2xl border p-6 transition-all ${
                    isCurrent
                      ? "border-primary/40 bg-card shadow-elegant"
                      : isComplete
                        ? "border-border/60 bg-card/40"
                        : "border-border/40 bg-card/20"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`mt-0.5 h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
                        isComplete
                          ? "bg-success/15 text-success"
                          : isCurrent
                            ? "bg-primary/15 text-primary animate-pulse-glow"
                            : "bg-secondary text-muted-foreground"
                      }`}
                    >
                      <StepIcon status={isCurrent ? "active" : step.status} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-3 flex-wrap">
                        <div>
                          <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-mono">
                            Stage {i + 1} · {step.workflow_stage || step.key}
                          </p>
                          <h3 className="text-lg font-semibold mt-0.5">
                            {step.title}
                          </h3>
                          {step.description && (
                            <p className="text-sm text-muted-foreground mt-1 max-w-prose">
                              {step.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded ${stageBadgeClass(
                              isCurrent ? "active" : step.status,
                            )}`}
                          >
                            {isCurrent ? "current" : step.status || "pending"}
                          </span>
                          {activeCase && (
                            <Button
                              variant={isComplete ? "outline" : "hero"}
                              size="sm"
                              disabled={stepBusy === step.key}
                              onClick={() => void toggleStep(step)}
                            >
                              {stepBusy === step.key ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : isComplete ? (
                                "Mark incomplete"
                              ) : (
                                "Mark complete"
                              )}
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="grid md:grid-cols-3 gap-4 mt-4">
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                            Rules applied ·{" "}
                            <span className="text-primary">{ruleCount}</span>
                          </p>
                          {step.rules.length === 0 ? (
                            <p className="text-xs text-muted-foreground">
                              No published rules indexed for this stage yet.
                            </p>
                          ) : (
                            <ul className="space-y-1.5">
                              {step.rules.slice(0, 4).map((r) => (
                                <li key={r.id} className="text-xs">
                                  <p className="font-medium truncate">
                                    {r.rule_title}
                                  </p>
                                  <p className="text-muted-foreground line-clamp-2">
                                    {r.rule_summary}
                                  </p>
                                  {r.source_url && (
                                    <a
                                      href={r.source_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-[10px] inline-flex items-center gap-1 text-primary hover:underline mt-0.5"
                                    >
                                      <ExternalLink className="h-3 w-3" />
                                      Source
                                    </a>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                            Required documents
                          </p>
                          {(step.aggregated_documents?.length ?? 0) +
                            (step.aggregated_forms?.length ?? 0) ===
                          0 ? (
                            <p className="text-xs text-muted-foreground">
                              Not stated in indexed sources.
                            </p>
                          ) : (
                            <ul className="space-y-1">
                              {(step.aggregated_forms ?? []).map((f) => (
                                <li
                                  key={`f-${f}`}
                                  className="text-xs flex items-center gap-1.5"
                                >
                                  <FileText className="h-3 w-3 text-primary" />
                                  Form: {f}
                                </li>
                              ))}
                              {(step.aggregated_documents ?? []).map((d) => (
                                <li
                                  key={`d-${d}`}
                                  className="text-xs flex items-center gap-1.5"
                                >
                                  <FileText className="h-3 w-3 text-muted-foreground" />
                                  {d}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                            Validations / deadlines
                          </p>
                          {(step.aggregated_validations?.length ?? 0) +
                            (step.aggregated_deadlines?.length ?? 0) ===
                          0 ? (
                            <p className="text-xs text-muted-foreground">
                              Not stated in indexed sources.
                            </p>
                          ) : (
                            <ul className="space-y-1">
                              {(step.aggregated_validations ?? []).map((v) => (
                                <li
                                  key={`v-${v}`}
                                  className="text-xs flex items-center gap-1.5"
                                >
                                  {isComplete ? (
                                    <CheckCircle2 className="h-3 w-3 text-success" />
                                  ) : (
                                    <AlertCircle className="h-3 w-3 text-warning" />
                                  )}
                                  {v}
                                </li>
                              ))}
                              {(step.aggregated_deadlines ?? []).map((d) => (
                                <li
                                  key={`dl-${d}`}
                                  className="text-xs flex items-center gap-1.5"
                                >
                                  <Clock className="h-3 w-3 text-muted-foreground" />
                                  {d}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>

                      {step.checklist?.length ? (
                        <div className="mt-4 border-t border-border/40 pt-3">
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                            Default checklist
                          </p>
                          <ul className="grid md:grid-cols-2 gap-1.5">
                            {step.checklist.map((c) => (
                              <li
                                key={c.key}
                                className="text-xs flex items-start gap-1.5"
                              >
                                <Circle className="h-3 w-3 text-muted-foreground mt-0.5" />
                                {c.label}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Workflows;
