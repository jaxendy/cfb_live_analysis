import requests
from backend import CFBD


class LiveGame:
    """Tracks one in-progress game.

    /live/plays returns the full game state: a top-level snapshot
    (status, period, clock, possession, down, distance), per-team
    aggregate stats, and every drive with its plays nested inside.
    poll() flattens the plays and merges them into a store keyed by
    play id, so history survives even if the endpoint's payload changes.
    """

    def __init__(self, game_id, cfbd=None):
        self.game_id = game_id
        self.plays = {}
        self.state = {}
        self.team_stats = []
        self.last_error = None
        self.cfbd = cfbd or CFBD()

    def poll(self):
        """Fetch current state and merge plays. Returns count of new plays."""
        try:
            payload = self.cfbd.get("/live/plays", gameId=self.game_id)
        except requests.RequestException as e:
            self.last_error = str(e)
            return 0

        self.last_error = None

        if isinstance(payload, dict):
            self.state = {k: v for k, v in payload.items()
                          if k not in ("drives", "teams")}
            self.team_stats = payload.get("teams", [])

        new = 0
        for p in self._extract(payload):
            k = self._key(p)
            if k not in self.plays:
                self.plays[k] = p
                new += 1
        return new

    @staticmethod
    def _extract(payload):
        """Flatten drives[].plays[], backfilling offense/defense from the drive."""
        if not isinstance(payload, dict):
            return []
        out = []
        for d in payload.get("drives", []):
            for raw in d.get("plays", []):
                p = dict(raw)
                p.setdefault("offense", d.get("offense"))
                p.setdefault("defense", d.get("defense"))
                p.setdefault("driveId", d.get("id"))
                p.setdefault("scoringOpportunity", d.get("scoringOpportunity"))
                # stats code expects 'ppa'; live feed calls it 'epa'
                if "ppa" not in p and "epa" in p:
                    p["ppa"] = p["epa"]
                out.append(p)
        return out

    @staticmethod
    def _key(p):
        if p.get("id") is not None:
            return p["id"]
        return (p.get("period"), p.get("clock"),
                p.get("offense"), p.get("playText"))

    @staticmethod
    def _seconds(p):
        c = p.get("clock")
        if isinstance(c, str) and ":" in c:
            m, s = c.split(":")
            try:
                return int(m) * 60 + int(s)
            except ValueError:
                return 0
        if isinstance(c, dict):
            return (c.get("minutes") or 0) * 60 + (c.get("seconds") or 0)
        return 0

    def all_plays(self):
        """Chronological: period ascending, clock descending."""
        return sorted(
            self.plays.values(),
            key=lambda p: (p.get("period") or 0, -self._seconds(p)),
        )

    @property
    def is_live(self):
        return self.state.get("status") == "In Progress"

    def __len__(self):
        return len(self.plays)