import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { ErrorState, Loading } from "../components/States";
import { buildGroups, loadView, recallFocus, rememberFocus, saveView, type FilmGroup, type StageItem } from "../home/adapter";
import { FirstRun } from "../home/FirstRun";
import { HorizonLine } from "../home/HorizonLine";
import { LibraryStatus } from "../home/LibraryStatus";
import { LivingFilmstrip } from "../home/LivingFilmstrip";
import { StageHero } from "../home/StageHero";
import { useAsync } from "../hooks";
import type { HomeData } from "../types";

const STAGE_DEBOUNCE_MS = 120;

export default function Home() {
  const { data, error, reload } = useAsync(() => api<HomeData>("/api/home"), []);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <Loading label="Opening your library" />;
  if (data.counts.movies + data.counts.episodes === 0) return <FirstRun hasFolders={data.counts.libraries > 0} />;
  return <HomeStage data={data} />;
}

function HomeStage({ data }: { data: HomeData }) {
  const groups = useMemo(() => buildGroups(data), [data]);
  const restored = useMemo(() => {
    const r = recallFocus();
    const g = r && groups.find((x) => x.id === r.group);
    return g && g.items.some((i) => i.key === r.key) ? r : null;
  }, [groups]);
  const [groupId, setGroupId] = useState<FilmGroup["id"]>((restored?.group as FilmGroup["id"]) ?? groups[0].id);
  const group = groups.find((g) => g.id === groupId) ?? groups[0];
  const [selectedKey, setSelectedKey] = useState(restored?.key ?? group.items[0].key);
  const [stageItem, setStageItem] = useState<StageItem>(
    () => group.items.find((i) => i.key === selectedKey) ?? group.items[0]);
  const [view, setView] = useState(loadView);
  const [anchor, setAnchor] = useState<number | null>(null);
  const [width, setWidth] = useState(0);
  const timer = useRef<number>(0);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const select = useCallback((item: StageItem) => {
    setSelectedKey(item.key);
    rememberFocus(groupId, item.key);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setStageItem(item), STAGE_DEBOUNCE_MS);
  }, [groupId]);

  const changeGroup = useCallback((id: FilmGroup["id"]) => {
    const g = groups.find((x) => x.id === id);
    if (!g) return;
    setGroupId(id);
    setSelectedKey(g.items[0].key);
    setStageItem(g.items[0]);
    rememberFocus(id, g.items[0].key);
  }, [groups]);

  const changeView = (v: "strip" | "grid") => { setView(v); saveView(v); };

  return (
    <div className="home" ref={root} data-testid="home-page">
      <StageHero item={stageItem} autofocus={!restored} />
      <HorizonLine anchor={view === "strip" ? anchor : null} width={width} />
      <LivingFilmstrip groups={groups} group={group} onGroup={changeGroup} selectedKey={selectedKey} onSelect={select}
        view={view} onView={changeView} restoreKey={restored?.key ?? null} onAnchor={setAnchor} />
      <LibraryStatus data={data} />
    </div>
  );
}
