import { memo } from "react"
import type { PersonProfile } from "@/api/types"
import { CardSection, ChapterTag, EntityLink } from "./CardSection"
import { EntityScenes } from "./EntityScenes"

interface PersonCardProps {
  profile: PersonProfile
  onEntityClick: (name: string, type: string) => void
  onChapterClick?: (ch: number) => void
  novelId?: string
}

// Category labels and ordering
const CATEGORY_LABELS: Record<string, string> = {
  family: "血亲关系",
  intimate: "亲密关系",
  hierarchical: "师承/主从",
  social: "社交关系",
  hostile: "敌对关系",
  other: "其他关系",
}
const CATEGORY_ORDER = ["family", "intimate", "hierarchical", "social", "hostile", "other"]

export const PersonCard = memo(function PersonCard({ profile, onEntityClick, onChapterClick, novelId }: PersonCardProps) {
  const { aliases, appearances, abilities, relations, items, experiences, stats } = profile
  const stateChanges = profile.state_changes ?? []
  const stateAsOf = profile.state_as_of

  // Group abilities by dimension
  const abilityGroups = new Map<string, typeof abilities>()
  for (const ab of abilities) {
    const group = abilityGroups.get(ab.dimension) ?? []
    group.push(ab)
    abilityGroups.set(ab.dimension, group)
  }

  return (
    <div className="space-y-0">
      {/* A. Basic Info */}
      <div className="border-b py-3">
        <div className="mb-1 flex items-center gap-3">
          <div className="bg-muted flex size-12 items-center justify-center rounded-full text-xl font-bold">
            {profile.name[0]}
          </div>
          <div>
            <h3 className="text-lg font-bold">{profile.name}</h3>
            {aliases.length > 0 && (
              <div className="text-muted-foreground text-xs">
                {aliases.map((a) => (
                  <span key={a.name} className="mr-2">
                    {a.name}
                    {a.first_chapter > 0 && (
                      onChapterClick ? (
                        <button
                          className="text-muted-foreground/50 ml-0.5 cursor-pointer hover:underline"
                          onClick={() => onChapterClick(a.first_chapter)}
                        >
                          (Ch.{a.first_chapter})
                        </button>
                      ) : (
                        <span className="text-muted-foreground/50 ml-0.5">(Ch.{a.first_chapter})</span>
                      )
                    )}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* B. Appearances — merged by description, latest first */}
      <CardSection title="外貌特征" defaultLimit={3}>
        {[...appearances].reverse().map((a, i) => {
          // Support both old ({chapter}) and new ({chapters}) format
          const chs: number[] = a.chapters ?? ((a as any).chapter != null ? [(a as any).chapter] : [])
          return (
            <div key={i} className="text-sm">
              {onChapterClick ? (
                <button
                  className="text-muted-foreground cursor-pointer text-xs hover:underline"
                  onClick={() => onChapterClick(chs[0])}
                >
                  {chs.length === 1
                    ? `Ch.${chs[0]}`
                    : chs.length <= 3
                      ? `Ch.${chs.join(",")}`
                      : `Ch.${chs[0]}–${chs[chs.length - 1]}(${chs.length}次)`
                  }
                </button>
              ) : (
                <span className="text-muted-foreground text-xs">
                  {chs.length === 1
                    ? `Ch.${chs[0]}`
                    : chs.length <= 3
                      ? `Ch.${chs.join(",")}`
                      : `Ch.${chs[0]}–${chs[chs.length - 1]}(${chs.length}次)`
                  }
                </span>
              )}
              <span className="ml-1.5">{a.description}</span>
            </div>
          )
        })}
      </CardSection>

      {/* C. Relations — grouped by category */}
      <CardSection title="人物关系" defaultLimit={15}>
        {CATEGORY_ORDER
          .filter(cat => relations.some(r => (r.category || "other") === cat))
          .flatMap(cat => [
            <div key={`cat-${cat}`} className="text-muted-foreground mt-2 text-xs font-medium first:mt-0">
              {CATEGORY_LABELS[cat] ?? cat}
            </div>,
            ...relations
              .filter(r => (r.category || "other") === cat)
              .map(rel => {
                const latest = rel.stages[rel.stages.length - 1]
                const totalEvidences = rel.stages.reduce(
                  (n, s) => n + (s.evidences?.length ?? (s.evidence ? 1 : 0)), 0,
                )
                return (
                  <div key={rel.other_person} className="text-sm pl-2">
                    <EntityLink
                      name={rel.other_person}
                      type="person"
                      onClick={onEntityClick}
                    />
                    <span className="text-muted-foreground mx-1">—</span>
                    <span>{latest?.relation_type ?? "未知"}</span>
                    {rel.stages.length > 1 && (
                      <span className="text-muted-foreground ml-1 text-xs">
                        ({rel.stages.map((s, si) => {
                          const chs: number[] = s.chapters ?? ((s as any).chapter != null ? [(s as any).chapter] : [])
                          if (chs.length === 0) return <span key={si}>{s.relation_type}</span>
                          const tag = chs.length === 1
                            ? `Ch.${chs[0]}`
                            : `Ch.${chs[0]}–${chs[chs.length - 1]}`
                          return (
                            <span key={si}>
                              {si > 0 && " → "}
                              {s.relation_type}(
                              {onChapterClick ? (
                                <button
                                  className="cursor-pointer hover:underline"
                                  onClick={() => onChapterClick(chs[0])}
                                >
                                  {tag}
                                </button>
                              ) : tag}
                              )
                            </span>
                          )
                        })})
                      </span>
                    )}
                    {totalEvidences > 0 && (
                      <details className="mt-0.5">
                        <summary className="text-muted-foreground text-[10px] cursor-pointer">
                          查看证据 ({totalEvidences})
                        </summary>
                        <div className="pl-2 mt-1 space-y-0.5">
                          {rel.stages.flatMap((s, si) =>
                            (s.evidences?.length ? s.evidences : s.evidence ? [s.evidence] : [])
                              .map((ev, ei) => (
                                <div key={`${si}-${ei}`} className="text-[11px] text-muted-foreground">
                                  「{ev}」
                                  {onChapterClick ? (
                                    <button
                                      className="ml-1 cursor-pointer opacity-60 hover:underline"
                                      onClick={() => onChapterClick(s.chapters[0])}
                                    >
                                      Ch.{s.chapters[0]}
                                    </button>
                                  ) : (
                                    <span className="ml-1 opacity-60">Ch.{s.chapters[0]}</span>
                                  )}
                                </div>
                              ))
                          )}
                        </div>
                      </details>
                    )}
                  </div>
                )
              }),
          ])}
      </CardSection>

      {/* D. Abilities */}
      <CardSection title="能力" defaultLimit={8}>
        {Array.from(abilityGroups.entries()).flatMap(([dim, abs]) => [
          <div key={`dim-${dim}`} className="text-muted-foreground mt-1 text-xs font-medium first:mt-0">
            {dim}
          </div>,
          ...abs.map((ab, i) => (
            <div key={`${dim}-${i}`} className="text-sm pl-2">
              <ChapterTag chapter={ab.chapter} onClick={onChapterClick} />
              <span className="ml-1.5 font-medium">{ab.name}</span>
              {ab.description && (
                <span className="text-muted-foreground ml-1">{ab.description}</span>
              )}
            </div>
          )),
        ])}
      </CardSection>

      {/* E. Items */}
      <CardSection title="物品关系" defaultLimit={5}>
        {items.map((it, i) => (
          <div key={i} className="text-sm">
            <ChapterTag chapter={it.chapter} onClick={onChapterClick} />
            <span className="ml-1.5">{it.action}</span>
            <EntityLink
              name={it.item_name}
              type="item"
              onClick={onEntityClick}
            />
            {it.description && (
              <span className="text-muted-foreground ml-1 text-xs">
                ({it.description})
              </span>
            )}
          </div>
        ))}
      </CardSection>

      {/* F. Footprint */}
      {(() => {
        const footprintMap = new Map<string, number>()
        for (const exp of experiences) {
          if (exp.location && !footprintMap.has(exp.location)) {
            footprintMap.set(exp.location, exp.chapter)
          }
        }
        if (footprintMap.size === 0) return null
        return (
          <CardSection title="足迹" defaultLimit={8}>
            {Array.from(footprintMap.entries()).map(([loc, ch]) => (
              <div key={loc} className="text-sm flex items-center gap-1.5">
                <ChapterTag chapter={ch} onClick={onChapterClick} />
                <EntityLink name={loc} type="location" onClick={onEntityClick} />
              </div>
            ))}
          </CardSection>
        )
      })()}

      {/* G. Experiences */}
      <CardSection title="经历" defaultLimit={5}>
        {[...experiences].reverse().map((exp, i) => (
          <div key={i} className="text-sm">
            <ChapterTag chapter={exp.chapter} onClick={onChapterClick} />
            <span className="ml-1.5">{exp.summary}</span>
            {exp.location && (
              <span className="text-muted-foreground ml-1">
                @<EntityLink
                  name={exp.location}
                  type="location"
                  onClick={onEntityClick}
                />
              </span>
            )}
          </div>
        ))}
      </CardSection>

      {/* Deterministic state reconstructed by replaying chapter deltas. */}
      {stateAsOf && (
        <CardSection title={`当前状态 · Ch.${stateAsOf.as_of_chapter}`} defaultLimit={12}>
          {(stateAsOf.martial_souls ?? []).map((name) => (
            <div key={`martial-soul-${name}`} className="text-sm">
              <span className="text-muted-foreground mr-1">武魂</span>{name}
            </div>
          ))}
          {(stateAsOf.soul_rings ?? []).map((ring, i) => (
            <div key={`soul-ring-${ring.martial_soul}-${ring.slot ?? i}`} className="text-sm">
              <span className="text-muted-foreground mr-1">
                {ring.martial_soul ? `${ring.martial_soul} · ` : ""}
                {ring.slot ? `第${ring.slot}魂环` : "魂环"}
              </span>
              {[ring.color, ring.age, ring.source, ...(ring.skills ?? [])].filter(Boolean).join(" · ")}
            </div>
          ))}
          {(stateAsOf.soul_skills ?? []).map((name) => (
            <div key={`soul-skill-${name}`} className="text-sm">
              <span className="text-muted-foreground mr-1">魂技</span>{name}
            </div>
          ))}
          {stateAsOf.soul_power_level && (
            <div className="text-sm">
              <span className="text-muted-foreground mr-1">魂力</span>{stateAsOf.soul_power_level}
            </div>
          )}
          {Object.entries(stateAsOf.abilities).flatMap(([dimension, names]) =>
            names.map((name) => (
              <div key={`ability-${dimension}-${name}`} className="text-sm">
                <span className="text-muted-foreground mr-1">{dimension}</span>{name}
              </div>
            )),
          )}
          {stateAsOf.organizations.map((org) => (
            <div key={`org-${org}`} className="text-sm">
              <span className="text-muted-foreground mr-1">势力</span>{org}
            </div>
          ))}
          {stateAsOf.items.map((item) => (
            <div key={`item-${item}`} className="text-sm">
              <span className="text-muted-foreground mr-1">持有</span>{item}
            </div>
          ))}
          {Object.entries(stateAsOf.relationships).map(([person, relation]) => (
            <div key={`relation-${person}`} className="text-sm">
              <span className="text-muted-foreground mr-1">关系</span>
              <EntityLink name={person} type="person" onClick={onEntityClick} />
              <span className="ml-1">— {relation}</span>
            </div>
          ))}
        </CardSection>
      )}

      {stateChanges.length > 0 && (
        <CardSection title="状态变更" defaultLimit={10}>
          {[...stateChanges].reverse().map((change, i) => (
            <div key={`${change.chapter}-${change.attribute}-${change.value}-${i}`} className="text-sm">
              <ChapterTag chapter={change.chapter} onClick={onChapterClick} />
              <span className="text-muted-foreground ml-1.5">{change.attribute}</span>
              <span className="ml-1">{change.action} {change.value}</span>
              {change.previous_value && (
                <span className="text-muted-foreground ml-1 text-xs">
                  （原：{change.previous_value}）
                </span>
              )}
            </div>
          ))}
        </CardSection>
      )}

      {/* H. Scenes */}
      {novelId && <EntityScenes novelId={novelId} entityName={profile.name} onChapterClick={onChapterClick} />}

      {/* I. Stats */}
      <div className="py-3">
        <details>
          <summary className="text-muted-foreground cursor-pointer text-xs font-medium uppercase tracking-wide">
            数据统计
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {Object.entries(stats).map(([k, v]) => (
              <div key={k} className="rounded-md bg-muted/50 px-2 py-1 text-sm">
                <span className="text-muted-foreground text-xs">{formatStatLabel(k)}</span>
                <div className="font-medium">{v}</div>
              </div>
            ))}
          </div>
        </details>
      </div>
    </div>
  )
})

function formatStatLabel(key: string): string {
  const labels: Record<string, string> = {
    chapter_count: "出场章节",
    first_chapter: "首次出场",
    last_chapter: "最后出场",
    relation_count: "关系数",
  }
  return labels[key] ?? key
}
