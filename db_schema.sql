-- Minimal schema; extend as needed.
CREATE TABLE IF NOT EXISTS fixtures (
  fixture_id BIGINT PRIMARY KEY,
  league_id INT NOT NULL,
  season INT NOT NULL,
  kickoff_utc TIMESTAMPTZ,
  status TEXT,
  home_team_id INT,
  away_team_id INT,
  ht_home_goals INT,
  ht_away_goals INT,
  ft_home_goals INT,
  ft_away_goals INT,
  last_update TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS odds (
  id BIGSERIAL PRIMARY KEY,
  fixture_id BIGINT REFERENCES fixtures(fixture_id),
  provider TEXT,
  market TEXT,
  selection TEXT,
  price NUMERIC,
  line NUMERIC,
  ts TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_odds_fixture_ts ON odds (fixture_id, ts);
