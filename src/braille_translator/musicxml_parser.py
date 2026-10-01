# Parser MusicXML de piano a AST; pentagrama 1 es mano derecha, 2 izquierda, y cada voz extra va como in-accord
import xml.etree.ElementTree as ET
from typing import List, Optional, Union

from .model import Chord, Measure, Note, Rest, Score

Container = Union[Note, Chord]


def _octave_musicxml_to_braille(octave_xml: int) -> int:
    # Las octavas cientificas coinciden con las Braille del Manual, limitadas a 1..7
    return max(1, min(7, octave_xml))


def _close_slur_group(group: List[Container]) -> None:
    # Hasta cuatro notas va el signo simple; mas largas llevan apertura y cierre
    if len(group) < 2:
        return
    if len(group) <= 4:
        for container in group[:-1]:
            container.slur = True
    else:
        group[0].slur_open = True
        group[-1].slur_close = True


def parse_musicxml(path: str) -> Score:
    tree = ET.parse(path)
    root = tree.getroot()

    score = Score()

    title_el = root.find(".//work/work-title")
    if title_el is not None and title_el.text:
        score.title = title_el.text.strip()

    part = root.find("part")
    if part is None:
        raise ValueError("MusicXML sin elemento <part>")

    # staff -> grupo de ligadura de expresion en curso (o None)
    active_slur = {1: None, 2: None}

    for m_el in part.findall("measure"):
        m_num = int(m_el.get("number", "0"))
        rh_measure = Measure(m_num)
        lh_measure = Measure(m_num)

        attributes = m_el.find("attributes")
        if attributes is not None:
            fifths = attributes.find("key/fifths")
            if fifths is not None:
                score.fifths = int(fifths.text)
            time = attributes.find("time")
            if time is not None:
                score.beats = int(time.find("beats").text)
                score.beat_type = int(time.find("beat-type").text)

        pending_chord: Optional[Chord] = None
        pending_staff = 1
        pending_voice = "1"
        voices = {1: {}, 2: {}}

        def voice_events(staff: int, voice: str) -> list:
            return voices[staff].setdefault(voice, [])
        pending_slur_start = False
        pending_slur_stop = False

        def flush_chord():
            nonlocal pending_chord, pending_slur_start, pending_slur_stop
            if pending_chord is None:
                return
            if len(pending_chord.notes) == 1:
                obj: Container = pending_chord.notes[0]
                obj.duration_type = pending_chord.duration_type
                obj.dots = pending_chord.dots
                obj.tie = pending_chord.tie or obj.tie
            else:
                obj = pending_chord
                # con todas las notas ligadas basta la ligadura de acorde
                if all(n.tie for n in obj.notes):
                    obj.tie = True
            voice_events(pending_staff, pending_voice).append(obj)

            group = active_slur[pending_staff]
            if group is None and pending_slur_start:
                active_slur[pending_staff] = [obj]
            elif group is not None:
                group.append(obj)
            if pending_slur_stop and active_slur[pending_staff]:
                _close_slur_group(active_slur[pending_staff])
                active_slur[pending_staff] = None

            pending_chord = None
            pending_slur_start = False
            pending_slur_stop = False

        for n_el in m_el.findall("note"):
            # Las notas de adorno y los silencios ocultos no ocupan tiempo escrito
            if n_el.find("grace") is not None or n_el.find("cue") is not None:
                continue
            if n_el.find("rest") is not None and n_el.get("print-object") == "no":
                continue
            staff_el = n_el.find("staff")
            staff = int(staff_el.text) if staff_el is not None else 1
            voice = n_el.findtext("voice", "1")

            dtype_el = n_el.find("type")
            dtype = dtype_el.text if dtype_el is not None else "quarter"
            n_dots = len(n_el.findall("dot"))

            if n_el.find("rest") is not None:
                flush_chord()
                pending_staff, pending_voice = staff, voice
                voice_events(staff, voice).append(Rest(dtype, n_dots))
                continue

            pitch = n_el.find("pitch")
            step = pitch.find("step").text
            octave = _octave_musicxml_to_braille(int(pitch.find("octave").text))
            alter_el = pitch.find("alter")
            alter = int(alter_el.text) if alter_el is not None else 0
            explicit = n_el.find("accidental") is not None

            tie_start = any(t.get("type") == "start" for t in n_el.findall("tie"))
            tie_stop = any(t.get("type") == "stop" for t in n_el.findall("tie"))
            slur_start = any(s.get("type") == "start" for s in n_el.findall("notations/slur"))
            slur_stop = any(s.get("type") == "stop" for s in n_el.findall("notations/slur"))

            note = Note(
                step=step,
                octave=octave,
                duration_type=dtype,
                alter=alter,
                dots=n_dots,
                explicit_accidental=explicit,
                tie=tie_start,
                tie_from_prev=tie_stop,
            )

            is_chord_member = n_el.find("chord") is not None
            if is_chord_member and pending_chord is not None and (staff, voice) == (pending_staff, pending_voice):
                pending_chord.notes.append(note)
                pending_slur_start = pending_slur_start or slur_start
                pending_slur_stop = pending_slur_stop or slur_stop
            else:
                flush_chord()
                pending_staff, pending_voice = staff, voice
                pending_chord = Chord(notes=[note], duration_type=dtype, dots=n_dots)
                pending_slur_start = slur_start
                pending_slur_stop = slur_stop

        flush_chord()
        for staff, measure in ((1, rh_measure), (2, lh_measure)):
            # Regla 5-12 sobre la numeracion de la tinta, donde la voz 1 es la superior
            lists = [voices[staff][v] for v in sorted(voices[staff], key=int, reverse=staff == 2)]
            if lists:
                measure.events = lists[0]
                measure.extra_voices = lists[1:]
        score.right.measures.append(rh_measure)
        score.left.measures.append(lh_measure)

    # Una ligadura sin cierre al final se cierra con lo acumulado
    for staff in (1, 2):
        if active_slur[staff]:
            _close_slur_group(active_slur[staff])
            active_slur[staff] = None

    return score
