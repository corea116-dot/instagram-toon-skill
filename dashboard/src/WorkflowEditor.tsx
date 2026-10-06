import { useEffect, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  type NodeProps,
  type Node,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Bot,
  Check,
  CirclePlus,
  Save,
  Sparkles,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import type { Snapshot, Stage, Workflow, Effort } from "../shared/types";
import { effortLabels } from "../shared/types";
import { api } from "./api";
import { Modal } from "./components";

type StageNode = Node<
  { stage: Stage; status: string; online: boolean },
  "stage"
>;
function StageBox({ data, selected }: NodeProps<StageNode>) {
  const n = data.stage;
  return (
    <div
      className={`flow-node ${selected ? "selected" : ""} ${data.online ? data.status : ""}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flow-top">
        <span className="stage-symbol">
          {n.model === "local" ? <ShieldCheck size={18} /> : <Bot size={18} />}
        </span>
        <span className="tiny">{n.role}</span>
        {data.status === "done" && <Check size={15} />}
      </div>
      <strong>{n.label}</strong>
      <small>
        {n.model === "local"
          ? "자동 처리"
          : `${n.model.replace("gpt-", "GPT-")} · ${effortLabels[n.effort]}`}
      </small>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { stage: StageBox };

export function WorkflowEditor({
  snapshot,
  online,
  onSaved,
  notify,
}: {
  snapshot: Snapshot;
  online: boolean;
  onSaved: () => void;
  notify: (s: string) => void;
}) {
  const [workflow, setWorkflow] = useState<Workflow>(
    snapshot.settings.workflow,
  );
  const [selected, setSelected] = useState(workflow.nodes[0].id);
  const [busy, setBusy] = useState(false);
  const [request, setRequest] = useState("");
  const [proposal, setProposal] = useState<Workflow | null>(null);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (!dirty) setWorkflow(snapshot.settings.workflow);
  }, [snapshot.settings.workflow.version, dirty]);
  const current = snapshot.runs.find((r) =>
    ["running", "approval", "paused", "error"].includes(r.status),
  );
  const node = workflow.nodes.find((n) => n.id === selected);
  const change = (next: Workflow) => {
    setWorkflow(next);
    setDirty(true);
  };
  const nodes: StageNode[] = workflow.nodes.map((n) => ({
    id: n.id,
    position: n.position,
    type: "stage",
    deletable: false,
    selected: n.id === selected,
    data: {
      stage: n,
      status: current?.stages[n.id]?.status ?? "waiting",
      online,
    },
  }));
  const onNodesChange = useCallback(
    (changes: NodeChange<StageNode>[]) => {
      const moved = applyNodeChanges(changes, nodes);
      if (changes.some((c) => c.type === "position"))
        change({
          ...workflow,
          nodes: workflow.nodes.map((n) => ({
            ...n,
            position: moved.find((m) => m.id === n.id)?.position ?? n.position,
          })),
        });
    },
    [workflow, nodes],
  );
  const onEdgesChange = (changes: EdgeChange[]) =>
    change({
      ...workflow,
      edges: applyEdgeChanges(changes, workflow.edges).map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      })),
    });
  const connect = (connection: Connection) =>
    change({
      ...workflow,
      edges: addEdge(
        { ...connection, id: crypto.randomUUID() },
        workflow.edges,
      ).map((e) => ({ id: e.id, source: e.source, target: e.target })),
    });
  const patch = (value: Partial<Stage>) =>
    change({
      ...workflow,
      nodes: workflow.nodes.map((n) =>
        n.id === selected ? { ...n, ...value } : n,
      ),
    });
  async function save(w = workflow) {
    setBusy(true);
    try {
      await api("/workflow", w, "PUT");
      setDirty(false);
      setProposal(null);
      notify("작업 설정을 저장했어요.");
      onSaved();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function add() {
    const last = workflow.nodes.find((n) => n.kind === "publish")!;
    const before = workflow.edges.filter((e) => e.target === last.id);
    const id = "step-" + crypto.randomUUID().slice(0, 8);
    const stage: Stage = {
      id,
      label: "추가 작업",
      kind: "custom",
      role: "추가 도우미",
      model: "gpt-6.1-sol",
      effort: "medium",
      instructions: "",
      position: { ...last.position },
    };
    change({
      ...workflow,
      nodes: [
        ...workflow.nodes.filter((n) => n.id !== last.id),
        stage,
        {
          ...last,
          position:
            last.position.x < 520
              ? { x: last.position.x + 260, y: last.position.y }
              : { x: 0, y: last.position.y + 170 },
        },
      ],
      edges: [
        ...workflow.edges.filter((e) => e.target !== last.id),
        ...before.map((e) => ({ ...e, target: id })),
        { id: "edge-" + id, source: id, target: last.id },
      ],
    });
    setSelected(id);
  }
  async function suggest() {
    setBusy(true);
    try {
      const result = await api<{ workflow: Workflow }>("/workflow/suggest", {
        message: request,
      });
      setProposal(result.workflow);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="section-title">
        <div>
          <p className="eyebrow">제작의 순서</p>
          <h1>작업 흐름</h1>
          <p>상자를 눌러 도우미를 바꾸고, 선을 이어 작업 순서를 정해요.</p>
        </div>
        <div className="button-row">
          <button className="secondary" onClick={add}>
            <CirclePlus size={17} />
            단계 추가
          </button>
          <button
            className="primary"
            onClick={() => void save()}
            disabled={busy || !dirty}
          >
            <Save size={17} />
            {busy ? "저장 중…" : "변경 저장"}
          </button>
        </div>
      </div>
      <div className="editor-layout">
        <section className="flow-panel">
          <div className="panel-bar">
            <span className="live-dot" />
            인스타툰 제작 · {workflow.nodes.length}단계
            <span className="subtle">상자를 움직여 배치할 수 있어요</span>
          </div>
          <div className="flow-canvas">
            <ReactFlow
              nodes={nodes}
              edges={workflow.edges.map((e) => ({
                ...e,
                animated:
                  online && current?.stages[e.target]?.status === "running",
              }))}
              nodeTypes={nodeTypes}
              ariaLabelConfig={{
                "controls.ariaLabel": "화면 크기 조절",
                "controls.zoomIn.ariaLabel": "확대",
                "controls.zoomOut.ariaLabel": "축소",
                "controls.fitView.ariaLabel": "전체 보기",
                "handle.ariaLabel": "단계 연결점",
                "edge.a11yDescription.default":
                  "연결선을 선택한 뒤 Delete 키로 지울 수 있어요.",
                "node.a11yDescription.default":
                  "상자를 선택하고 방향키로 이동할 수 있어요.",
              }}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={connect}
              onNodeClick={(_e, n) => setSelected(n.id)}
              fitView
              fitViewOptions={{ padding: 0.12, minZoom: 0.65, maxZoom: 1 }}
              minZoom={0.35}
              maxZoom={1.6}
              deleteKeyCode={["Backspace", "Delete"]}
            >
              <Background gap={22} color="#dce1d6" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
          <p className="panel-foot">
            필수 검사 단계는 유지돼요. 모델 변경은 진행 중인 작업에도 반영하고,
            단계 추가·순서는 새 작업부터 적용해요.
          </p>
          <div className="step-selector" aria-label="편집할 도우미 선택">
            {workflow.nodes.map((n, i) => (
              <button
                key={n.id}
                aria-pressed={selected === n.id}
                onClick={() => setSelected(n.id)}
              >
                <span>{i + 1}</span>
                {n.label}
              </button>
            ))}
          </div>
        </section>
        <aside className="inspector">
          {node && (
            <>
              <p className="eyebrow">선택한 단계</p>
              <h2>{node.label}</h2>
              <label>
                단계 이름
                <input
                  value={node.label}
                  onChange={(e) => patch({ label: e.target.value })}
                />
              </label>
              <label>
                도우미 이름
                <input
                  value={node.role}
                  onChange={(e) => patch({ role: e.target.value })}
                />
              </label>
              {node.model === "local" ? (
                <div className="gentle-note">
                  <ShieldCheck size={19} />
                  <p>
                    정해진 기준으로 자동 처리하는 단계예요. 별도의 AI 모델을
                    사용하지 않아요.
                  </p>
                </div>
              ) : (
                <>
                  <label>
                    사용할 모델
                    <select
                      value={node.model}
                      onChange={(e) => {
                        const model = snapshot.connection.models.find(
                          (m) => m.model === e.target.value,
                        );
                        patch({
                          model: e.target.value,
                          effort: model?.supportedReasoningEfforts.some(
                            (x) => x.reasoningEffort === node.effort,
                          )
                            ? node.effort
                            : (model?.supportedReasoningEfforts[0]
                                ?.reasoningEffort ?? "medium"),
                        });
                      }}
                    >
                      {!snapshot.connection.models.length && (
                        <option>{node.model}</option>
                      )}
                      {snapshot.connection.models.map((m) => (
                        <option key={m.model} value={m.model}>
                          {m.displayName}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    생각하는 깊이 <span className="subtle">추론 강도</span>
                    <select
                      value={node.effort}
                      onChange={(e) =>
                        patch({ effort: e.target.value as Effort })
                      }
                    >
                      {(
                        snapshot.connection.models.find(
                          (m) => m.model === node.model,
                        )?.supportedReasoningEfforts ?? [
                          { reasoningEffort: node.effort },
                        ]
                      ).map((e) => (
                        <option
                          key={e.reasoningEffort}
                          value={e.reasoningEffort}
                        >
                          {effortLabels[e.reasoningEffort]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    이 도우미에게 줄 지시
                    <textarea
                      rows={5}
                      value={node.instructions}
                      onChange={(e) => patch({ instructions: e.target.value })}
                      placeholder="이 단계에서 꼭 지켜야 할 내용을 적어주세요."
                    />
                  </label>
                  {node.kind === "art" && (
                    <small>
                      이 설정은 그림 제작을 맡은 도우미의 설정이에요. 실제
                      그림은 기존 그림 도구로 만들어요.
                    </small>
                  )}
                </>
              )}
              {node.kind === "custom" && (
                <button
                  className="text-button danger"
                  onClick={() => {
                    change({
                      ...workflow,
                      nodes: workflow.nodes.filter((n) => n.id !== node.id),
                      edges: workflow.edges.filter(
                        (e) => e.source !== node.id && e.target !== node.id,
                      ),
                    });
                    setSelected(workflow.nodes[0].id);
                  }}
                >
                  이 추가 단계 삭제
                </button>
              )}
            </>
          )}
        </aside>
      </div>
      <section className="assistant-box">
        <div className="assistant-symbol">
          <Sparkles size={23} />
        </div>
        <div>
          <h3>말로 설명하듯 바꿔보세요</h3>
          <p>
            원하는 변경을 Codex에게 설명하면, 적용 전에 변경안을 보여드려요.
          </p>
          <div className="input-action">
            <input
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              placeholder="예: 대본 도우미를 Astra로 바꾸고 더 깊게 생각하게 해줘"
            />
            <button
              className="secondary"
              disabled={busy || !request.trim()}
              onClick={() => void suggest()}
            >
              {busy ? "변경안 만드는 중…" : "변경안 만들기"}
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </section>
      {proposal && (
        <Modal title="Codex가 만든 변경안" onClose={() => setProposal(null)}>
          <p>아래 설정을 저장하면 현재 제작 중인 도우미 설정에도 반영돼요.</p>
          <div className="proposal-list">
            {proposal.nodes.map((n) => (
              <div key={n.id}>
                <strong>{n.label}</strong>
                <span>
                  {n.model === "local"
                    ? "자동 처리"
                    : `${n.model} · ${effortLabels[n.effort]}`}
                </span>
                {n.instructions && <small>{n.instructions}</small>}
              </div>
            ))}
          </div>
          <div className="modal-actions">
            <button className="secondary" onClick={() => setProposal(null)}>
              취소
            </button>
            <button
              className="primary"
              disabled={busy}
              onClick={() => void save(proposal)}
            >
              이대로 적용
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
