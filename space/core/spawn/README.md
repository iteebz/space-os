# SPAWN: Constitutional identity registry.

Tracks who's who: identity → constitution → provider/model.

**Quick start:**
```
spawn list                              # see registrations
spawn register <identity> <constitution> <provider> <model>
```

**Example:**
```
spawn register zealot zealot.md claude claude-opus
spawn register harbinger harbinger.md gemini gemini-2.5-pro
spawn list
```

**How it works:**
1. Constitution lives at `constitutions/<name>.md`
2. Each identity maps: name → constitution → provider/model
3. Bridge/memory/knowledge use spawn for identity lookup

**Commands:**
```
spawn list
spawn register <identity> <constitution> <provider> <model>
spawn unregister <identity>
spawn <identity>                        # launch with identity
```

**Storage:** `.space/spawn.db`
