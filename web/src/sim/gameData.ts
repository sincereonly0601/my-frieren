/**
 * 載入 `export_web_sim_data.py` 產生之靜態資料並建立索引。
 */

import type {
  EncountersBundleJson,
  EndingJson,
  IncidentEventJson,
  MajorEventJson,
  WhimEncounterJson,
} from "./types";

import encountersBundle from "./data/encounters.json";
import endingsList from "./data/endings.json";
import incidentAftermath from "./data/incident_aftermath.json";
import incidentsList from "./data/incidents.json";
import majorsList from "./data/majors.json";
import whimEncountersList from "./data/whim_encounters.json";
import whimNpcKeysOrder from "./data/whim_npc_keys_order.json";

export const MAJOR_EVENTS: MajorEventJson[] = majorsList as unknown as MajorEventJson[];
export const MAJOR_BY_AGE: Map<number, MajorEventJson> = new Map(
  MAJOR_EVENTS.map((m) => [m.age_year, m]),
);

export const ALL_INCIDENTS: IncidentEventJson[] =
  incidentsList as unknown as IncidentEventJson[];
export const INCIDENT_AFTERMATH_BY_ID: Record<string, string[][]> =
  incidentAftermath as Record<string, string[][]>;

export const ENCOUNTERS: EncountersBundleJson =
  encountersBundle as unknown as EncountersBundleJson;

export const ENDINGS_LIST: EndingJson[] = endingsList as unknown as EndingJson[];
export const ENDINGS_BY_KEY: Map<string, EndingJson> = new Map(
  ENDINGS_LIST.map((e) => [e.key, e]),
);

export const WHIM_ENCOUNTERS: WhimEncounterJson[] =
  whimEncountersList as unknown as WhimEncounterJson[];
export const WHIM_BY_KEY: Map<string, WhimEncounterJson> = new Map(
  WHIM_ENCOUNTERS.map((w) => [w.key, w]),
);

export const WHIM_ENCOUNTER_KEYS_ORDER: readonly string[] = whimNpcKeysOrder as string[];
