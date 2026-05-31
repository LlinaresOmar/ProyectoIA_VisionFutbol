import argparse
import json
from html import escape
from pathlib import Path


STATUS_COLORS = {
    "PLAY_ANALYZABLE": "#2f9e44",
    "NO_BALL_VISIBLE": "#f08c00",
    "CLOSE_UP": "#7048e8",
    "UNKNOWN": "#868e96",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un panel HTML a partir de las metricas JSON de un clip."
    )
    parser.add_argument(
        "--stats",
        required=True,
        help="Ruta del JSON de metricas generado por video_analise.py.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ruta HTML de salida. Si no se indica, se genera junto al JSON.",
    )
    return parser.parse_args()


def rgb_to_css(rgb):
    if not rgb:
        return "#666666"

    values = [max(0, min(255, int(round(value)))) for value in rgb]
    return f"rgb({values[0]}, {values[1]}, {values[2]})"


def percent(value, total):
    if not total:
        return 0.0
    return (value / total) * 100


def load_stats(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_status_bars(status_counts, frames_analyzed):
    blocks = []
    for status, count in sorted(status_counts.items()):
        width = percent(count, frames_analyzed)
        color = STATUS_COLORS.get(status, "#495057")
        blocks.append(
            f"""
            <div class="metric-row">
              <div class="metric-label">
                <span>{escape(status)}</span>
                <strong>{count} ({width:.1f}%)</strong>
              </div>
              <div class="bar-track">
                <div class="bar-fill" style="width:{width:.2f}%; background:{color}"></div>
              </div>
            </div>
            """
        )
    return "\n".join(blocks)


def build_team_cards(teams):
    if not teams:
        return '<p class="muted">Sin equipos agrupados todavia.</p>'

    cards = []
    for team_id, info in sorted(teams.items()):
        color = rgb_to_css(info.get("avg_rgb"))
        tracks = info.get("tracks", 0)
        cards.append(
            f"""
            <article class="team-card">
              <div class="swatch" style="background:{color}"></div>
              <div>
                <h3>{escape(team_id)}</h3>
                <p>{tracks} tracks asociados</p>
              </div>
            </article>
            """
        )
    return "\n".join(cards)


def build_pass_cards(summary, possession):
    frames_by_team = possession.get("frames_by_team", {})
    total_possession_frames = sum(int(value or 0) for value in frames_by_team.values())

    def possession_pct(team):
        return percent(int(frames_by_team.get(team, 0) or 0), total_possession_frames)

    return f"""
      <article class="card"><p class="muted">Team 1 passes</p><strong>{summary.get("team_1_passes", 0)}</strong><p class="muted">{possession_pct("team_1"):.1f}% posesion</p></article>
      <article class="card"><p class="muted">Team 2 passes</p><strong>{summary.get("team_2_passes", 0)}</strong><p class="muted">{possession_pct("team_2"):.1f}% posesion</p></article>
      <article class="card"><p class="muted">Pass candidates</p><strong>{summary.get("pass_candidates", 0)}</strong><p class="muted">eventos aproximados</p></article>
      <article class="card"><p class="muted">Referee candidates</p><strong>{summary.get("role_counts", {}).get("referee_candidate", 0)}</strong><p class="muted">tracks outlier</p></article>
    """


def build_tracks_table(tracks):
    rows = []
    sorted_tracks = sorted(
        tracks,
        key=lambda item: item.get("frames_seen", 0),
        reverse=True,
    )[:12]

    for track in sorted_tracks:
        team_id = track.get("team_id") or "-"
        role = track.get("role") or "-"
        color = rgb_to_css(track.get("avg_jersey_rgb"))
        rows.append(
            f"""
            <tr>
              <td>#{track.get("track_id")}</td>
              <td>{escape(str(team_id))}</td>
              <td>{escape(str(role))}</td>
              <td>{track.get("frames_seen", 0)}</td>
              <td>{track.get("avg_conf", 0)}</td>
              <td>{track.get("total_distance_px", 0)}</td>
              <td><span class="table-swatch" style="background:{color}"></span></td>
            </tr>
            """
        )

    return "\n".join(rows)


def build_events_table(events):
    if not events:
        return '<p class="muted">Sin eventos de pase detectados en este clip.</p>'

    rows = []
    for event in events[:20]:
        rows.append(
            f"""
            <tr>
              <td>{escape(str(event.get("type", "-")))}</td>
              <td>{event.get("frame", "-")}</td>
              <td>{escape(str(event.get("team", "-")))}</td>
              <td>#{event.get("from_track_id", "-")}</td>
              <td>#{event.get("to_track_id", "-")}</td>
              <td>{event.get("distance_px", "-")}</td>
            </tr>
            """
        )

    return f"""
      <table>
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Frame</th>
            <th>Equipo</th>
            <th>Desde</th>
            <th>Hacia</th>
            <th>Dist. balon px</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    """


def build_html(stats):
    metadata = stats.get("metadata", {})
    summary = stats.get("summary", {})
    tracks = stats.get("tracks", [])
    teams = stats.get("teams", {})
    frames = stats.get("frames", [])
    possession = stats.get("possession", {})
    events = stats.get("events", [])
    frames_analyzed = int(summary.get("frames_analyzed", 0))
    ball_visible = int(summary.get("ball_visible_frames", 0))
    ball_ratio = percent(ball_visible, frames_analyzed)

    data_json = json.dumps(
        {
            "frames": frames,
            "statusColors": STATUS_COLORS,
            "possession": possession.get("timeline", []),
        }
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Football AI Analysis Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --ink: #161616;
      --muted: #6c757d;
      --line: #deded6;
      --accent: #176b5d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 22px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: 28px; line-height: 1.1; }}
    h2 {{ font-size: 18px; margin-bottom: 14px; }}
    h3 {{ font-size: 15px; }}
    .muted {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .card, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .card strong {{
      display: block;
      font-size: 26px;
      margin-top: 6px;
    }}
    .sections {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .metric-row {{ margin-bottom: 12px; }}
    .metric-label {{
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .bar-track {{
      height: 10px;
      background: #ecece5;
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      width: 0;
      transition: width 700ms ease;
    }}
    .team-list {{
      display: grid;
      gap: 10px;
    }}
    .team-card {{
      display: flex;
      align-items: center;
      gap: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfbf8;
    }}
    .swatch {{
      width: 42px;
      height: 42px;
      border-radius: 6px;
      border: 1px solid rgba(0,0,0,.18);
    }}
    canvas {{
      width: 100%;
      height: 120px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfbf8;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    .table-swatch {{
      display: inline-block;
      width: 26px;
      height: 16px;
      border-radius: 4px;
      border: 1px solid rgba(0,0,0,.18);
    }}
    .note {{
      margin-top: 10px;
      font-size: 13px;
      color: var(--muted);
      line-height: 1.45;
    }}
    @media (max-width: 860px) {{
      header, .sections {{ display: block; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      section {{ margin-bottom: 14px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <p class="muted">Football AI Analysis</p>
        <h1>{escape(Path(metadata.get("input", "clip")).name)}</h1>
      </div>
      <p class="muted">Tracker: {escape(str(metadata.get("tracker", "-")))} | Modelo: {escape(str(metadata.get("model", "-")))}</p>
    </header>

    <div class="grid">
      <article class="card"><p class="muted">Frames analizados</p><strong>{frames_analyzed}</strong></article>
      <article class="card"><p class="muted">Balon visible</p><strong>{ball_visible}</strong><p class="muted">{ball_ratio:.1f}%</p></article>
      <article class="card"><p class="muted">Tracks unicos</p><strong>{summary.get("unique_player_tracks", 0)}</strong></article>
      <article class="card"><p class="muted">Track maximo</p><strong>{summary.get("max_track_length_frames", 0)}</strong><p class="muted">frames</p></article>
    </div>

    <div class="grid">
      {build_pass_cards(summary, possession)}
    </div>

    <div class="sections">
      <section>
        <h2>Estados Del Clip</h2>
        {build_status_bars(summary.get("status_counts", {}), frames_analyzed)}
      </section>
      <section>
        <h2>Equipos Por Color</h2>
        <div class="team-list">{build_team_cards(teams)}</div>
        <p class="note">team_1 y team_2 salen de clusters de color por track. referee_candidate es un outlier estable de color respecto a esos clusters, por tanto es heuristico.</p>
      </section>
    </div>

    <section>
      <h2>Timeline De Estados</h2>
      <canvas id="timeline" width="1080" height="140"></canvas>
      <p class="note">La posesion se estima asociando el balon al pie del track mas cercano dentro de un umbral. Un pase candidato aparece cuando cambia el poseedor a otro track del mismo equipo en una ventana temporal plausible.</p>
    </section>

    <section style="margin-top:18px">
      <h2>Tracks Principales</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Equipo</th>
            <th>Rol</th>
            <th>Frames</th>
            <th>Conf.</th>
            <th>Distancia px</th>
            <th>Color</th>
          </tr>
        </thead>
        <tbody>{build_tracks_table(tracks)}</tbody>
      </table>
    </section>

    <section style="margin-top:18px">
      <h2>Eventos De Pase</h2>
      {build_events_table(events)}
    </section>
  </main>
  <script>
    const reportData = {data_json};
    const canvas = document.getElementById('timeline');
    const ctx = canvas.getContext('2d');
    const frames = reportData.frames || [];
    const colors = reportData.statusColors || {{}};

    function drawTimeline(progress) {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!frames.length) return;
      const count = Math.floor(frames.length * progress);
      const barWidth = canvas.width / frames.length;
      for (let i = 0; i < count; i++) {{
        const frame = frames[i];
        ctx.fillStyle = colors[frame.status] || '#868e96';
        ctx.fillRect(i * barWidth, 26, Math.max(1, barWidth), 58);
      }}
      ctx.fillStyle = '#161616';
      ctx.font = '16px Arial';
      ctx.fillText('Inicio', 0, 112);
      ctx.fillText('Final', canvas.width - 38, 112);
    }}

    let start;
    function animate(timestamp) {{
      if (!start) start = timestamp;
      const progress = Math.min(1, (timestamp - start) / 900);
      drawTimeline(progress);
      if (progress < 1) requestAnimationFrame(animate);
    }}
    requestAnimationFrame(animate);
  </script>
</body>
</html>
"""


def main():
    args = parse_args()
    stats_path = Path(args.stats)
    stats = load_stats(stats_path)
    output_path = Path(args.output) if args.output else stats_path.with_suffix(".html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html(stats), encoding="utf-8")
    print(f"Panel generado: {output_path}")


if __name__ == "__main__":
    main()
