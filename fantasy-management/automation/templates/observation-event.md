# {{ entity.display_name }} – {{ classification }}

**Zeitpunkt:** {{ created_at }}  
**Target Sets:** {{ target_set_ids }}  
**Profil:** {{ profile_id }}  
**Schweregrad:** {{ severity }}

## Beobachtung

{{ observation.summary }}

### Signale

{{ observation.signals }}

## Interpretation

{{ interpretation.summary }}

**Konfidenz:** {{ interpretation.confidence }}

### Offene Konflikte

{{ interpretation.unresolved_conflicts }}

## Handlungseffekt

**Perspektive:** {{ decision_effect.perspective }}  
**Dringlichkeit:** {{ decision_effect.urgency }}

{{ decision_effect.summary }}

- Vorherige Handlung: {{ decision_effect.previous_action }}
- Neue Handlung: {{ decision_effect.new_action }}

## Evidenz

{{ evidence }}

## Zustandsvergleich

### Vorher

{{ previous_state }}

### Aktuell

{{ current_state }}
