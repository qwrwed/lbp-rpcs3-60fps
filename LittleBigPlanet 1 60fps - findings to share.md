# LittleBigPlanet 1 60fps in RPCS3 - findings to share

Game: LittleBigPlanet GOTY (BCES00611) with update 1.30. The code and data addresses below match Papy's BCES00141 1.30 notes; patch addresses are for the update EBOOT's PPU hash `PPU-545c1abbf1c562d60fca7435401f020beab76b53`.

## What holds the game at 30fps
- The game's VBlank handler (0x37a498) signals a flip every 2 VBlanks. Patching 0x37a4c4 and 0x37a4e4 to `li r0,1` (0x38000001) and 0x37a4bc to a branch (0x48000014) lets it run at 60.
- At 60 the whole game runs about 2.1x fast (measured: a 0.3 s stick hold moves Sackboy 93 px at 30fps, 193 px at 60fps).

## Why there is no single timestep to halve
- No SPU program (5,437 functions in RPCS3's SPU cache) loads 1/30, 1/60, 30 or 60 as a constant, and the EBOOT holds no double 1/30 or 1/60.
- Halving the PPU's 1/30 float constants does not change game speed (Papy's tests).
- Movement is per tick. Sackboy's walk speed grows by about 3 units per tick (next ≈ 0.995 × speed + 3.003) and caps at 30 per tick.

## Where the per-tick values live
- Sackboy's tuning is a plain-text character settings file, `gamedata/creatures/yellowhead.cha` (magic `CHAt`) in `data.farc`. It holds walk and air speeds and accelerations (`WalkSpeedMaxDesired 30`, `WalkSpeedMaxAcceleration 3`, `AirSpeedMaxDesired 22.5`, `AirSpeedMaxAcceleration 2.4`, jetpack values) and frame counts (`FramesTillDrown 900`, `FramesFromFireDeathTillRespawn 35` and others).
- Soft-body settings are plain-text `.sph` files (magic `SSPt`): damping, wind, spring iterations.
- Physics materials are binary `.mat` files with `gravityMultiplier` and `airResistanceMultiplier` (field order in the Craftworld Toolkit's `RMaterial.java`).
- World gravity is the `PEffector` gravity vector, default (0, -2.7, 0), stored with each level. Halving it in memory halves Sackboy's fall acceleration.
- Jump strength is in none of the number fields of Sackboy's character settings or of the gravity record (each halved in memory, jump unchanged).

## How to load edited game files
- The game checks every file against the SHA-1 listed for its path in `USRDIR/output/brg_patch.map` (entry: path, timestamp, size, SHA-1, GUID).
- Editing a file inside `data.farc` makes the hash check fail and the game crashes at load.
- What works: write the edited file at its game path under `USRDIR/` (for example `USRDIR/gamedata/creatures/yellowhead.cha`), put its new size and SHA-1 in that map entry, and leave `data.farc` untouched. The game then loads the loose file.
- Compressed binary files (`MATb` and similar): 4-byte magic, revision, dependency-table offset, a compressed flag, a chunk count, per-chunk compressed and unpacked sizes, zlib data, then the dependency table. Rebuilding with zlib level 9 reproduces the original bytes.
- Tested: walk speed 30 → 15 in `yellowhead.cha` halves Sackboy's walk.

## Results so far with per-tick scaling
- Sackboy's gravity follows `gravityMultiplier` in `gamedata/materials/yellowhead.mat` as loaded (changing it in memory afterwards does nothing). At 0.25 and 30fps, a jump lasts about 4× as long (about 2.7 s against 0.7 s).
- The game reads no jump settings from files; jump strength is in code.
- At 60fps with gravity multiplier 0.25, Sackboy walks much slower than at 30fps: with walk 30 / acceleration 3 he covers about a third of the normal 60fps distance, and with 15 / 0.75 about a seventh of the 30fps distance. Hypothesis: floor grip scales with gravity, so friction or damping per tick also needs scaling.
- At 60fps with gravity multiplier 1.0 and walk 15 / 0.75, a 0.3 s hold moves Sackboy about 60 px (30fps original: 93 px). Setting the material's traction to 4 alongside gravity 0.25 does not restore the walk (still about 13 px).
- Per-tick data at 60fps (walk 15 / 0.75, gravity multiplier 1.0), from a position copy in game units: speed rises 0.75 per tick to the 15 cap; after release it falls by about 0.8 per tick. That matches friction ≈ 0.3 × gravity per tick (gravity per tick = 2.7 × the material's multiplier), so quartering gravity also quarters the slowdown, as 60fps needs.
- The game multiplies Sackboy's walk acceleration by the material's gravity multiplier: with multiplier 0.25, `WalkSpeedMaxAcceleration` 0.75 gives 0.19 per tick and 3 gives 0.75 per tick (measured live). So for 60fps, keep the accelerations at their original values and set the gravity multiplier to 0.25; that quarters both.
- With that (walk speed 15, accelerations original, gravity multiplier 0.25) at 60fps, per tick: acceleration 0.75, top speed 15, braking about 0.81 after release (braking also uses the scaled acceleration). In real time that equals the 30fps original (2,700 units/s² and 900 units/s).
- Jump at 60fps (per tick, while A is held): speed rises 12.0, 21.2, 27.2, 30.9, 33.1, 34.4, 34.9, closing about 40% of the gap to roughly 35 each tick; then it falls by gravity plus a little drag. The target does not depend on gravity (halving the world gravity vectors leaves it), and changing the only 35.0 in the EBOOT's data, or every 35.0 in memory, has no effect. Jump strength is not in any file.
- Jump strength is the creature's `jumpModifier` (Toolkit `PCreature`), a float at creature object +0x92c next to `speedModifier` (+0x928) and `strengthModifier` (+0x930); +0x914 points to the character settings object. The creature constructor stores 1.0 into all three at 0x35a20–0x35a34 (`lfs f13,-0x7b20(r2)`, then `stfs f13` to each), and the jump code reads it at 0x4d538.
- The jump's peak speed per tick is about 35 × jumpModifier² (measured live at 60fps: 1.0 → 35.0, 0.9 → 28.4, 0.75 → 19.4, 0.5 → 7.9). With 0.7071 the peak is about 17.2.
- With gravity multiplier 0.25 and jumpModifier 0.7071 at 60fps, a jump lasts about 1.29 s and rises about 277 units.
- 30fps original jump in the same units (A held 0.12 s): speed per tick 12.1, 19.3, 23.2, 24.9, then falling about 2.8 per tick; about 1.3–1.4 s in the air, about 160–175 units high.
- Jump boost code (0x4d590–0x4d6b8): the jump-frame counter n (creature +0x910 → +0x4c, reset when above 9 at 0x4d500) sets f13 = 1.48^n (1.48 is the TOC float at 0x86a5a4, loaded at 0x4d5a8); the jump impulse vector is divided by it, so each tick's boost is about 1/1.48 of the previous one. Measured at 30fps: boost per tick (steps plus gravity) 14.8, 9.9, 6.6, 4.4.
- For 60fps in real time the boost per tick should be a quarter, the per-tick decay √1.48 ≈ 1.2166 (nearest reachable TOC float: 1.2 at TOC offset 0x8228) and the frame limit doubled.
- Live test at 60fps (gravity 0.25, data edits, jumpModifier 0.5 on all creatures, the 1.48 constant set to 1.2): speed per tick 5.0, 7.4, 9.4, 10.8, 11.9, 12.7, 13.2; jump height about 181 units (30fps original: 160–175).
- Patch for that (PPU hash above), as RPCS3 patch lines:
  - `[ be32, 0x0004d5a8, 0xc0028228 ]` boost decay loads 1.2 (TOC float at 0x8696c8).
  - `[ be32, 0x0004d538, 0xc162851c ]` the jump code's jump modifier loads 0.5 (TOC float at 0x8699bc).
  - `[ be32, 0x0059ae98, 0xc002851c ]` and `[ be32, 0x0059b158, 0xc002851c ]` the other two readers of the jump modifier load 0.5. With only the first reader patched, the jump stays far too strong (peak about 23 per tick).
- Result with all four lines at 60fps (plus D, E, gravity 0.25 and the character edits): speed per tick 4.7, 7.1, 8.9, 10.3, 11.4, 12.1, 12.6, then falling; height 168–173 units, about 0.8 s from leaving the ground to landing at about 53 FPS (0.71 s of game time). 30fps original, measured the same way: 174.8 units, 0.70 s.
- Walk on screen (0.3 s stick holds from the pod's left side): 30fps original about 85 px per hold, 60fps setup about 62 px at 52–55 FPS.
- The game's speed follows its frame rate once these per-tick values are halved, so the setup only plays at normal speed when RPCS3 holds 60 FPS. On a Steam Deck (Desktop Mode) a story level runs at about 27 FPS even unpatched at 30, limited by RPCS3's RSX thread on the CPU; the pod reaches 51–55 FPS.
- On a Steam Machine (RPCS3 0.0.43-20375, Desktop Mode) the full setup holds 59.9–60.0 FPS in The Meerkat Kingdom, standing and walking, at about 50–58% CPU.
- Pod decorations sway twice as fast with the 60fps setup (sway period from 12 s recordings, 30fps original against 60fps setup):
  - star: 3.28 s → 1.67 s;
  - lamp: 3.98 s → 1.99 s;
  - butterflies: 5.28–5.35 s → 2.67 s.
- Animation clock: the TOC float 30.0 at 0x8699ec drives it. Doubling it live slows the pod decorations to their 30fps speed, and bisecting all 25 copies of 30.0 in the data leaves only this one.
  - It has six readers. The one at 0x1fe6c divides by it (`fdivs`) right after checking an animation's frame count; the others add it or multiply by it in other code.
  - Patch for that reader alone, loading the TOC float 60.0 at 0x869b04 instead: `[ be32, 0x0001fe6c, 0xc0028664 ]`.
  - With it at 60fps the pod decorations sway at 30fps speed: star 3.30 s, lamp 3.93 s.
  - Sackboy's running legs run twice as fast with the 60fps setup, measured from footstep sounds while he runs across the pod: a step every 0.20 s (0.40 s cycle) in the 30fps original, every 0.10 s with the 60fps setup. His running speed on screen is the same in both (about 200 px/s at 960 px width).
  - None of these change the running step rhythm at 60fps when changed live: `FootAnimationSpeed` in the character settings object (0.25, 0.5, 1.0); the seven 1/30 floats, 1/15 at 0x871ba0, 1/60 at 0x86d8f4 and the nine 0.03 floats (all halved together); 33.333 at 0x86cfa4 (halved); 30.0 at 0x8699ec (doubled). The EBOOT holds no double 30, 1/30 or 1/60.
  - Files that exist only on the disc (listed in the disc's `USRDIR/output/blurayguids.map`, stored in its `data.farc`) also load from `USRDIR/` of the update when a new entry is appended to `brg_patch.map` (the disc entry's 36 bytes with the new size and SHA-1, and the entry count raised). RPCS3's log shows the game opening and reading them in full.
  - Sackboy's walk clips are `gamedata/mesh_library/player_character/sack_boy_pinched_anims/walk_slow.anim`, `walk_medium.anim` and `walk_fast.anim`: revision 0x132, 43 bones, 13 frames, `fps` 30 (32-bit integers at unpacked bytes 692 and 696). Setting `fps` to 15 in all three changes nothing: steps stay 0.10 s apart.
  - Sackboy's animations advance one frame per tick. The walk clips are 13 frames: 0.43 s per cycle at 30 ticks/s, 0.22 s at 60. Doubling them to 26 frames (`mod/anim_resample.py`, an interpolated frame between each pair) brings the 60fps step rhythm to one step every 0.21 s, matching the 30fps original (0.20 s).
  - `mod/anim_install.py` doubles every clip in `player_character/sack_boy_pinched_anims/` (213 files: 159 at revision 0x132, the rest 0x134–0x272) and installs them as loose files with map entries. Revisions from 0x271 have a 4-byte branch descriptor after the dependency offset; `lbpmod.py` handles it.
  - Looping clips get an interpolated frame from the last frame back to the first; the rest end on their last frame. A clip counts as looping when its last frame's bone rotations sit within 1.5 times its median frame-to-frame change of its first frame, or "loop" is in its name: 103 of 213 qualify (walks, idles, stands, swim strokes, push and pull among them).
  - With all 213 doubled, steps at 60fps are 0.21 s apart.
  - The hanging prize bubbles at the start of The Meerkat Kingdom move about 1.78× fast with the 60fps setup (periods of three bubbles: 0.80, 0.57, 0.70 s in the 30fps original; 0.45, 0.32, 0.40 s at 60fps). Setting patch K's 60.0 back to 30.0 live leaves them unchanged, so they do not play through K's reader.
  - What moves is the icon inside each bubble swelling and shrinking. With the four collectible clips (`common_objects/collectible_sphere/collectible_sphere_icon_anim_boil/swell.anim`, `common_objects/collectable_resources/resource_sack_anim_boil/swell.anim`) frame-doubled, the periods become 1.02, 0.72 and 0.94 s: about 1.3× slow. Doubling these overshoots.
  - Pulse shape per tick (icon size): the 30fps original jumps to full size, shrinks over about 19 ticks, then grows back over about 5 (24-tick cycle). The 60fps original has the same shape in ticks (27-tick cycle). With all four clips doubled it shrinks over about 42 ticks and grows over about 20 (62-tick cycle); 60fps needs about 38 and 10.
  - The clips are `swell` (11 frames) and `boil` (5 frames), both 30 fps and not looping.
  - Doubling only the two `swell` clips (the game reads them, per RPCS3's log) leaves the pulses exactly as in the 60fps original (0.45, 0.32, 0.40 s). The change with all four doubled therefore comes from `boil`: 5 → 9 frames took the cycle from 27 to 62 ticks, not in proportion to the frame count.
  - Level mechanics run per tick too. In Get a Grip the King at the start bobs every 1.98 s in the 30fps original and every 1.00 s with the 60fps setup (patch K on), and a blue glow pulses every 0.54 s against 0.27 s.
  - The King is joint-driven. Joints (Toolkit `PJoint`) keep `animationRange`, `animationTime`, `animationPhase`, `animationSpeed`, `animationPause` as consecutive floats in memory, with `animationTime` in frames (default 60). Doubling the 121 heap copies of [range, 60.0, 0, speed, pause] live at 30fps doubles his period to 3.98 s. The glow is unchanged by it, so it runs on something else.
  - Memory search while running at 60fps, following pointers up to three levels from Sackboy's creature object: only bone-transform blocks (rotation terms within ±1, positions in the hundreds) cycle at 0.20 s. No field there ramps and wraps like a playback position, as floats or as small integers.
  - Holding the stick into the pod's left wall, Sackboy steps in place with the 60fps setup (cycle 0.20 s, unchanged by this reader, the other five, the 1/30 constants or `FootAnimationSpeed` 0.25–1.0); in the 30fps original he turns to the wall in a pushing pose instead.
- RPCS3 0.0.43-20375 aborts at boot (SIGABRT, nothing in the log) with a modified update EBOOT; the original update EBOOT boots.
- Objects: all 14 material files in the map have `gravityMultiplier` at unpacked byte 25 (revisions 0x159, 0x24d–0x26e). Multiplying each by 0.25 gives every object the 60fps gravity per tick. Revision 0x159 files have no compressed-flag byte before the chunk table.
  - The jump-frame limit stays at 9: raising it to 18 (`[ be32, 0x0004d500, 0x2f800012 ]`) makes the jump far too strong at 60fps (peak 25.8 per tick, about 530 units high).
- Hypothesis for the remaining gap: the slide after the stick is released decays per tick inside the physics engine, so it is cut short at 60fps. The EBOOT holds no settings table for engine damping or friction, only save-file field names (`CollideDamping`, `ExtraDamping`, `TweakGravity` and similar).
