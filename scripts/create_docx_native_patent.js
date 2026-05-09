const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageBreak, LevelFormat,
  TabStopType, ImageRun
} = require("docx");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "output", "patent");
fs.mkdirSync(OUT, { recursive: true });

const DOCX_OUT = path.join(OUT, "Weather_Adaptive_Pollinator_Activity_Prediction_DOCX_NATIVE.docx");

const NAVY = "1B3A6B";
const TEAL = "2E7D8C";
const LIGHT_BLUE = "D6EAF8";
const MID_BLUE = "AED6F1";
const DARK_GRAY = "2C3E50";
const ACCENT = "1A5276";
const WHITE = "FFFFFF";
const LIGHT_GRAY = "F2F4F4";
const MED_GRAY = "D5D8DC";
const GREEN_FILL = "A9DFBF";
const PURPLE_FILL = "D7BDE2";
const ORANGE_FILL = "FDEBD0";
const RED_FILL = "FADBD8";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function H1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 120 },
    children: [new TextRun({ text, bold: true, size: 30, font: "Arial", color: NAVY })]
  });
}

function H2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 100 },
    children: [new TextRun({ text, bold: true, size: 26, font: "Arial", color: TEAL })]
  });
}

function H3(text) {
  return new Paragraph({
    spacing: { before: 180, after: 70 },
    children: [new TextRun({ text, bold: true, size: 23, font: "Arial", color: ACCENT })]
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    alignment: opts.center ? AlignmentType.CENTER : AlignmentType.JUSTIFIED,
    spacing: { before: 60, after: 80, line: 276, lineRule: "auto" },
    children: [new TextRun({ text, size: 22, font: "Arial", color: DARK_GRAY, ...opts.run })]
  });
}

function spacer(pts = 1) {
  return new Paragraph({ spacing: { before: 0, after: pts * 20 }, children: [new TextRun("")] });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function divider(color = TEAL) {
  return new Paragraph({
    spacing: { before: 100, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color, space: 1 } },
    children: [new TextRun("")]
  });
}

function sectionBox(title, content) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [new TableCell({
          borders: {
            top: { style: BorderStyle.SINGLE, size: 8, color: NAVY },
            bottom: { style: BorderStyle.SINGLE, size: 2, color: MED_GRAY },
            left: { style: BorderStyle.SINGLE, size: 8, color: NAVY },
            right: { style: BorderStyle.SINGLE, size: 2, color: MED_GRAY }
          },
          shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 140, right: 140 },
          children: [new Paragraph({ children: [new TextRun({ text: title, bold: true, size: 24, font: "Arial", color: NAVY })] })]
        })]
      }),
      new TableRow({
        children: [new TableCell({
          borders: {
            top: noBorder,
            bottom: { style: BorderStyle.SINGLE, size: 2, color: MED_GRAY },
            left: { style: BorderStyle.SINGLE, size: 8, color: NAVY },
            right: { style: BorderStyle.SINGLE, size: 2, color: MED_GRAY }
          },
          margins: { top: 100, bottom: 100, left: 200, right: 140 },
          children: content
        })]
      })
    ]
  });
}

function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.w || 3120, type: WidthType.DXA },
    columnSpan: opts.colSpan,
    borders: opts.noBorders ? noBorders : borders,
    shading: { fill: opts.fill || WHITE, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: opts.pad || 70, bottom: opts.pad || 70, left: 110, right: 110 },
    children: Array.isArray(text)
      ? text
      : [new Paragraph({
          alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
          children: [new TextRun({
            text,
            bold: opts.bold || false,
            size: opts.size || 20,
            font: opts.font || "Arial",
            color: opts.color || DARK_GRAY
          })]
        })]
  });
}

function headerCell(text, w, fill = NAVY) {
  return cell(text, { w, fill, color: WHITE, bold: true, center: true, size: 18 });
}

function phaseBlock(label, color, fill, items) {
  return [
    new TableRow({
      children: [new TableCell({
        width: { size: 9360, type: WidthType.DXA },
        borders: {
          top: { style: BorderStyle.SINGLE, size: 6, color },
          bottom: noBorder,
          left: { style: BorderStyle.SINGLE, size: 6, color },
          right: { style: BorderStyle.SINGLE, size: 2, color }
        },
        shading: { fill, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 40, left: 140, right: 140 },
        children: [new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 20, font: "Arial", color })] })]
      })]
    }),
    new TableRow({
      children: [new TableCell({
        width: { size: 9360, type: WidthType.DXA },
        borders: {
          top: noBorder,
          bottom: { style: BorderStyle.SINGLE, size: 4, color },
          left: { style: BorderStyle.SINGLE, size: 6, color },
          right: { style: BorderStyle.SINGLE, size: 2, color }
        },
        margins: { top: 60, bottom: 80, left: 200, right: 140 },
        children: items.map(item => new Paragraph({
          spacing: { before: 20, after: 20 },
          children: [new TextRun({ text: item, size: 19, font: "Courier New", color: DARK_GRAY })]
        }))
      })]
    }),
    new TableRow({
      children: [new TableCell({
        borders: noBorders,
        margins: { top: 12, bottom: 12, left: 140, right: 140 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "▼", size: 22, font: "Arial", color: MED_GRAY })] })]
      })]
    })
  ];
}

function architectureDiagram() {
  const phases = [
    { label: "INPUT STREAMS", color: NAVY, fill: MID_BLUE, items: ["[1] Weather API + Farm Station", "[2] Camera / Acoustic / IoT Sensors", "[3] Crop Phenology + Bloom Density"] },
    { label: "DATA PROCESSING CORE", color: "1A6645", fill: GREEN_FILL, items: ["[4] Synchronize - timestamp, field, crop match", "[5] Clean - impute missing, remove noise", "[6] Feature Store - rolling windows, stress scores"] },
    { label: "ENSEMBLE PREDICTION ENGINE", color: "7D3C98", fill: PURPLE_FILL, items: ["[7] Tree Models - GBM + Random Forest", "[8] Temporal Network - short-term sequence pattern", "[9] Uncertainty Layer - Bayesian / Quantile range"] },
    { label: "DECISION & OUTPUT LAYER", color: "A04000", fill: ORANGE_FILL, items: ["[10] Calibrate - probability and confidence", "[11] Risk Score - demand minus predicted activity", "[12] Recommend - timing alerts and caution flags"] },
    { label: "FEEDBACK & RETRAINING LOOP", color: NAVY, fill: LIGHT_BLUE, items: ["[13] Observe - store later visit counts", "[14] Compare - forecast versus actual outcome", "[15] Update - reweight models and recalibrate"] }
  ];
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360], rows: phases.flatMap(p => phaseBlock(p.label, p.color, p.fill, p.items)) });
}

function pipelineDiagram() {
  const phases = [
    { phase: "START", color: NAVY, fill: MID_BLUE, items: ["READ - weather, crop, pollinator streams ingested", "VALIDATE - range checks and timestamp alignment", "PATCH - missing values fitted or flagged"] },
    { phase: "FEATURE ENGINEERING", color: "1A6645", fill: GREEN_FILL, items: ["WEATHER LAG - 15 to 120 min rolling signal windows", "STRESS SCORE - heat, wind shock, and rain recovery", "BLOOM DEMAND - crop-stage pollination need index"] },
    { phase: "PREDICT", color: "7D3C98", fill: PURPLE_FILL, items: ["BASE MODELS - parallel activity estimates from all learners", "META LAYER - weighted combined forecast via stacking", "CONFIDENCE - agreement score + calibration correction"] },
    { phase: "DELIVER", color: "A04000", fill: ORANGE_FILL, items: ["ACTIVITY INDEX - field-level numeric score from 0 to 1", "HEAT MAP - spatial deficit risk across field blocks", "ACTION ALERT - spray, scout, or hive timing guidance"] },
    { phase: "STORE & LEARN", color: "117864", fill: "A2D9CE", items: ["PREDICTION LOG - versioned forecast snapshot saved", "FIELD RESULT - observed visit counts recorded", "LEARNING QUEUE - batch queued for next model update"] }
  ];
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360], rows: phases.flatMap(p => phaseBlock(`PHASE: ${p.phase}`, p.color, p.fill, p.items)) });
}

function ensembleDiagram() {
  const layers = [
    { name: "INPUT FEATURE VECTORS", fill: MID_BLUE, color: NAVY, cols: ["Weather Vector", "Crop Vector", "Activity Vector"], descs: ["Current + lagged values", "Stage and bloom density", "Recent visit signal"] },
    { name: "BASE LEARNERS", fill: PURPLE_FILL, color: "7D3C98", cols: ["GBM", "Random Forest", "Temporal Net"], descs: ["Nonlinear weather effects", "Noise-resistant baseline", "Short-term sequence"] },
    { name: "UNCERTAINTY", fill: ORANGE_FILL, color: "A04000", cols: ["Quantile Model", "Bayesian Model", "State Classifier"], descs: ["Upper and lower bounds", "Confidence spread", "Active/inactive state"] },
    { name: "STACKING", fill: "A2D9CE", color: "117864", cols: ["Meta Learner", "Calibration", "Disagreement Flag"], descs: ["Combines estimates", "Corrects probability", "Raises caution level"] },
    { name: "FINAL OUTPUT", fill: LIGHT_BLUE, color: NAVY, cols: ["Activity 0.84", "Risk: Low", "Peak: 9-11 AM"], descs: ["Score", "Deficit result", "Timing recommendation"] }
  ];
  const rows = [];
  for (let li = 0; li < layers.length; li++) {
    const l = layers[li];
    rows.push(new TableRow({
      children: [
        cell(l.name, { w: 1800, fill: l.fill, bold: true, center: true, color: l.color, size: 17 }),
        ...l.cols.map((c, i) => cell([
          new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: c, bold: true, size: 19, font: "Arial", color: NAVY })] }),
          new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: l.descs[i], size: 17, font: "Arial", color: DARK_GRAY })] })
        ], { w: 2520 }))
      ]
    }));
    if (li < layers.length - 1) rows.push(new TableRow({ children: [cell("▼", { colSpan: 4, noBorders: true, center: true, size: 22, color: MED_GRAY })] }));
  }
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [1800, 2520, 2520, 2520], rows });
}

function learningLoopDiagram() {
  const phases = [
    { label: "COLLECT", color: NAVY, fill: MID_BLUE, items: ["Forecast Log: saved prediction history with timestamps", "Actual Visits: manual or sensor visit counts post-event", "Weather Context: conditions recorded during outcome window"] },
    { label: "CHECK & DIAGNOSE", color: "7D3C98", fill: PURPLE_FILL, items: ["Error: calculate deviation of forecast from actual", "Drift: detect weather shift versus training distribution", "Quality: identify sensor gaps and coverage issues"] },
    { label: "RETRAIN", color: "1A6645", fill: GREEN_FILL, items: ["Base Models: update selected learners with new labeled data", "Weights: rebalance ensemble importance scores", "Calibration: repair probability scale if drift confirmed"] },
    { label: "VALIDATE", color: "A04000", fill: ORANGE_FILL, items: ["Time Split: past predicts future with no data leakage", "Metrics: MAE, AUC, and Brier score tested", "Approval: deploy only if validated metrics improve"] },
    { label: "DEPLOY & MONITOR", color: "117864", fill: "A2D9CE", items: ["Model Version: release tracked by identifier", "Dashboard: confidence metrics updated in farmer view", "Monitor: next cycle begins and watches for drift"] }
  ];
  const rows = phases.flatMap(p => phaseBlock(`STAGE: ${p.label}`, p.color, p.fill, p.items));
  rows.push(new TableRow({
    children: [cell("Loop repeats every prediction cycle - the model improves with field feedback", { fill: "EAF2FF", center: true, bold: true, color: TEAL, size: 19 })]
  }));
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360], rows });
}

function riskMatrix() {
  const data = [
    ["Condition", "Calm / Sunny", "Windy / Cloudy", "Recent Rain"],
    ["Early Bloom", "High activity\nSufficient visits", "Medium risk\nWatch conditions", "Medium risk\nDelay likely"],
    ["Full Bloom", "High activity\nOptimal window", "High risk\nScout and intervene", "High risk\nSupport pollination"],
    ["Late Bloom", "Medium activity\nDemand falling", "High risk\nFlag deficit zone", "Low activity\nRecovery delay"],
    ["Recommended Action", "Normal monitoring\nSpray off-window", "Scout + recheck\nAvoid active window", "Hive adjustment\nReport deficit zone"]
  ];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2340, 2340, 2340, 2340],
    rows: data.map((row, r) => new TableRow({
      children: row.map((text, c) => {
        const isHead = r === 0 || c === 0;
        let fill = isHead ? (r === 0 ? NAVY : ACCENT) : (r % 2 ? WHITE : LIGHT_GRAY);
        let color = isHead ? WHITE : DARK_GRAY;
        if (!isHead && text.toLowerCase().includes("high risk")) { fill = RED_FILL; color = "922B21"; }
        if (!isHead && text.toLowerCase().includes("medium risk")) { fill = ORANGE_FILL; color = "A04000"; }
        if (!isHead && text.toLowerCase().includes("high activity")) { fill = "D5F5E3"; color = "1A6645"; }
        return cell(text, { w: 2340, fill, color, bold: isHead, center: true, size: 18 });
      })
    }))
  });
}

function dashboardDiagram() {
  const card = (label, value, sublabel, fill, color) => cell([
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: label, size: 17, font: "Arial", color })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: value, bold: true, size: 32, font: "Arial", color })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: sublabel, size: 17, font: "Arial", color: DARK_GRAY })] })
  ], { w: 3120, fill });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [3120, 3120, 3120],
    rows: [
      new TableRow({ children: [
        card("ACTIVITY INDEX", "0.82", "High - sufficient visits", "D5F5E3", "1A6645"),
        card("CONFIDENCE", "91%", "Model agreement strong", LIGHT_BLUE, NAVY),
        card("PEAK WINDOW", "09:30-11:45", "Optimal visit period", ORANGE_FILL, "A04000")
      ]}),
      new TableRow({ children: [cell("", { colSpan: 3, noBorders: true })] }),
      new TableRow({ children: [
        card("TEMPERATURE", "Favorable", "Within optimal range", MID_BLUE, NAVY),
        card("WIND", "Moderate", "Slight disturbance risk", ORANGE_FILL, "A04000"),
        card("RAIN", "Recovered", "No spray inhibition", GREEN_FILL, "1A6645")
      ]}),
      new TableRow({ children: [cell("", { colSpan: 3, noBorders: true })] }),
      new TableRow({ children: [
        card("PESTICIDE", "Avoid Peak", "09:00-12:00 restricted", RED_FILL, "922B21"),
        card("SCOUTING", "Check Low Zones", "Blocks B3 and C1", ORANGE_FILL, "A04000"),
        card("HIVE PLAN", "Hold Position", "Move only if risk persists", "D5F5E3", "1A6645")
      ]})
    ]
  });
}

function priorArtTable() {
  const data = [
    ["US20220125029A1", "Insect monitoring via detection devices", "Detects presence but does not forecast activity from live weather streams", "Transforms monitored data into weather-adaptive forecasts"],
    ["WO2020162926A1", "Population movement monitoring", "Monitoring-oriented design lacks ensemble prediction", "Uses observed activity as feedback for ensemble training"],
    ["US10064395B2", "Beehive management monitoring", "Hive-centric rather than crop-field forecast oriented", "Predicts field activity and deficit risk"],
    ["US12075762B2", "Electronic bee monitoring", "Tracks data without weather-adaptive window prediction", "Forecasts peak windows and operational alerts"],
    ["WO2021060374A1", "Automatic pollination using imaging", "Hardware solution does not forecast natural behavior", "Supports natural pollination before artificial intervention"],
    ["CN104255442A", "Airflow-based pollen transfer", "Mechanical only, no ecological prediction", "Provides data-driven timing recommendations"],
    ["WO2011090041A1", "Vibration-assisted pollination", "Does not model weather-sensitive behavior", "Determines whether natural activity is adequate"]
  ];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [1600, 2200, 2480, 3080],
    rows: [
      new TableRow({ children: [headerCell("Patent ID", 1600), headerCell("Description", 2200), headerCell("Research Gap", 2480), headerCell("Inventive Contribution", 3080)] }),
      ...data.map((r, i) => new TableRow({ children: r.map((v, c) => cell(v, { w: [1600, 2200, 2480, 3080][c], fill: i % 2 === 0 ? WHITE : LIGHT_GRAY, size: 18 })) }))
    ]
  });
}

function inventorTable() {
  const sigA = fs.readFileSync(path.join(OUT, "visual_assets", "aarav_kashyap_singh_signature.png"));
  const sigB = fs.readFileSync(path.join(OUT, "visual_assets", "jai_dev_meena_signature.png"));
  const sigRun = (buf) => new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new ImageRun({ data: buf, type: "png", transformation: { width: 230, height: 62 } })]
  });
  const fields = [
    ["Full Name", "Aarav Kashyap Singh", "Jai Dev Meena"],
    ["Mobile Number", "6281328903", "8209926739"],
    ["Email (Personal)", "aaravkashyap1203@gmail.com", "mjai9127@gmail.com"],
    ["UID / Registration", "12305324", "12318662"],
    ["Institution", "Lovely Professional University, Punjab-144411, India", "Lovely Professional University, Punjab-144411, India"]
  ];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2200, 3580, 3580],
    rows: [
      new TableRow({ children: [headerCell("Field", 2200), headerCell("Inventor A", 3580), headerCell("Inventor B", 3580)] }),
      ...fields.map(([f, a, b], i) => new TableRow({ children: [cell(f, { w: 2200, fill: LIGHT_BLUE, bold: true, color: NAVY }), cell(a, { w: 3580 }), cell(b, { w: 3580 })] })),
      new TableRow({ children: [cell("Signature", { w: 2200, fill: LIGHT_BLUE, bold: true, color: NAVY }), cell([sigRun(sigA)], { w: 3580 }), cell([sigRun(sigB)], { w: 3580 })] })
    ]
  });
}

function titlePage() {
  return [
    spacer(8),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "INVENTION DISCLOSURE FORM", bold: true, size: 48, font: "Arial", color: NAVY })] }),
    divider(NAVY),
    spacer(4),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Weather-Adaptive Pollinator Activity Prediction", bold: true, size: 34, font: "Arial", color: TEAL })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "Using Ensemble Learning and Real-Time Meteorological Streams", bold: true, size: 28, font: "Arial", color: ACCENT })] }),
    divider(TEAL),
    spacer(6),
    body("Annexure 3b - Complete Filing", { center: true }),
    spacer(3),
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Lovely Professional University", bold: true, size: 24, font: "Arial", color: NAVY })] }),
    body("Punjab - 144411, India", { center: true }),
    body("Filing Type: Provisional Patent Application", { center: true }),
    pageBreak()
  ];
}

function paragraphList(items, numbered = false) {
  return items.map(t => new Paragraph({
    numbering: { reference: numbered ? "numbers" : "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text: t, size: 22, font: "Arial", color: DARK_GRAY })]
  }));
}

const description = "This invention presents a modular, weather-aware computational platform for estimating and forecasting pollinator activity across agricultural fields and ecological study sites. Rather than treating pollination as a fixed seasonal occurrence governed by static rules, the system continuously reads changing ambient conditions and combines them with crop phenological stage, field spatial context, and real-time pollinator movement records. Weather inputs may originate from public meteorological API feeds, dedicated farm weather stations, low-cost IoT sensing nodes, optical camera counters, acoustic event detectors, and manual field survey entries.";
const problem = "In many farms, pollinator activity is still judged through rough field observation or broad seasonal weather assumptions. This is insufficient because a small shift in wind speed, ambient temperature, rainfall duration, humidity, or cloud cover can change pollinator movement within the same day. Existing monitoring technologies can count insects or track hive movement, but they generally cannot tell the farmer what is likely to occur in the next few hours.";

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }
    ]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, font: "Arial", color: NAVY }, paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: "Arial", color: TEAL }, paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } }
    ]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    headers: { default: new Header({ children: [new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 1 } }, children: [new TextRun({ text: "INVENTION DISCLOSURE | ", bold: true, size: 16, font: "Arial", color: NAVY }), new TextRun({ text: "Weather-Adaptive Pollinator Activity Prediction | Lovely Professional University", size: 16, font: "Arial", color: DARK_GRAY })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 4, color: TEAL, space: 1 } }, tabStops: [{ type: TabStopType.CENTER, position: 4680 }, { type: TabStopType.RIGHT, position: 9360 }], children: [new TextRun({ text: "Confidential - Academic & IPR Filing", size: 16, font: "Arial", color: DARK_GRAY }), new TextRun({ text: "\tEnsemble ML Pollinator System\t", size: 16, font: "Arial", color: DARK_GRAY })] })] }) },
    children: [
      ...titlePage(),
      H1("1. Inventor Details"), divider(), inventorTable(), body("External Inventors: None. This invention is the original work of the two internal inventors listed above."), pageBreak(),
      H1("2. Description of the Invention"), divider(), body(description), body("All collected data streams are aligned into synchronized short-duration time windows, cleaned to remove noise and sensor failures, and converted into computational indicators such as wind disturbance index, rainfall recovery coefficient, heat stress score, daylight phase position, bloom demand level, and short-term visit trend."), body("Results are delivered through an integrated dashboard, spatial heat map, alert panel, and API endpoint so farmers, agricultural advisors, and ecological researchers can make informed decisions regarding pesticide spray scheduling, hive placement timing, field scouting, and pollination support."), H1("3. Problem Addressed by the Invention"), divider(), body(problem), body("Consequently, farmers may unknowingly apply pesticides during active pollination windows, relocate hives at sub-optimal times, miss short high-activity windows, or fail to detect a pollination deficit until after the crop flowering stage has passed."), pageBreak(),
      H1("4. Objectives of the Invention"), divider(), sectionBox("Primary Objectives", paragraphList([
        "To construct a weather-responsive prediction framework that joins live meteorological streams with crop phenology records, field spatial data, and observed pollinator movement.",
        "To deploy more than one machine learning model family so the system remains stable when the weather pattern changes suddenly or an individual sensor fails.",
        "To generate an activity index, visitation probability, expected visit count, peak activity window, pollination deficit risk score, and calibrated confidence value.",
        "To present results through dashboard cards, heat maps, time-series panels, pesticide caution alerts, and field recommendations.",
        "To enable continuous improvement by comparing forecast outputs with later field observations and updating model weights."
      ], true)), pageBreak(),
      H1("5. State of the Art, Research Gap, and Novelty"), divider(), body("The table below identifies prior art references, the limitation of each, and the specific contribution of this invention."), priorArtTable(), pageBreak(),
      H1("6. Detailed Technical Description"), divider(), H2("6.1 Core Modules"), H3("Real-Time Meteorological Stream Interface"), body("Collects temperature, humidity, wind, rainfall, solar radiation, cloud cover, dew point, pressure, and forecast values."), H3("Pollinator Observation Ingestion Module"), body("Accepts camera counts, acoustic events, visit logs, hive notes, trap readings, and manual survey entries."), H3("Feature Engineering Engine"), body("Builds lag values, moving averages, wind shock score, rainfall recovery time, heat stress score, daylight phase, and bloom demand."), H3("Ensemble Learning Prediction Core"), body("Runs gradient boosting, random forest, temporal, uncertainty, and state classification models in parallel and combines their outputs through stacking and calibration."), pageBreak(),
      H1("7. Working Model Diagrams"), divider(), H2("Figure 1 - Complete Prediction Architecture"), architectureDiagram(), pageBreak(), H2("Figure 2 - Prediction Pipeline Flowchart"), pipelineDiagram(), pageBreak(), H2("Figure 3 - Continuous Learning Loop"), learningLoopDiagram(), pageBreak(), H2("Figure 4 - Dashboard and Alert Interface"), dashboardDiagram(), pageBreak(), H2("Figure 5 - Pollination Deficit Risk Matrix"), riskMatrix(), pageBreak(), H2("Figure 6 - Ensemble Model Stack"), ensembleDiagram(), pageBreak(),
      H1("8. Claims"), divider(), ...paragraphList([
        "A computer-implemented system for weather-adaptive pollinator activity prediction comprising a real-time meteorological stream interface, a pollinator observation ingestion module, a crop phenology and landscape module, a feature engineering engine, and an ensemble learning prediction core.",
        "The system of claim 1, wherein the meteorological interface receives temperature, humidity, precipitation, wind speed, solar radiation, cloud cover, dew point, pressure, and forecasted weather values.",
        "The system of claim 1, wherein the ensemble core comprises at least two model families selected from gradient boosted decision trees, random forests, temporal neural networks, Bayesian models, quantile regression models, and logistic classifiers.",
        "The system of claim 1, wherein the output comprises activity index, visitation probability, expected visit count, peak activity time window, pollination deficit risk classification, and confidence score.",
        "The system of claim 1, further comprising an alert module configured to recommend pesticide avoidance windows, hive placement timing, field scouting zones, and pollination support actions.",
        "A method of predicting pollinator activity comprising receiving real-time weather data, receiving field observation records, computing rolling feature windows, processing the windows through a plurality of machine learning models, calibrating combined outputs, and transmitting a field-level forecast."
      ], true), pageBreak(),
      H1("9. Results and Advantages"), divider(), sectionBox("Key Technical Advantages", paragraphList([
        "Forecasts future activity instead of only recording present counts.",
        "Handles sudden changes in wind, rain, heat, humidity, and solar radiation.",
        "Reduces pesticide exposure risk by identifying active pollination windows.",
        "Supports crop yield improvement through early deficit detection.",
        "Uses multiple model families for stability under noisy field conditions.",
        "Provides interpretable outputs for farmers, researchers, and policymakers."
      ])), H1("10. Commercialisation Potential"), divider(), body("The invention is commercially relevant to precision agriculture platforms, pollination management services, smart weather advisory systems, apiary technology, ecological monitoring networks, and crop insurance risk analytics."), H1("11. Filing Options and Disclosure Status"), divider(), body("Filing Recommendation: Provisional Patent Application. The invention is at a conceptual and developmental stage and may later be supported with prototype results and field validation."), body("Public Disclosure Status: The invention has not been publicly disclosed, commercially used, or presented at any conference or publication prior to this academic filing draft."), pageBreak(),
      H1("No Objection Certificate"), divider(), body("This is to certify that Lovely Professional University and its associates shall have no objection if Lovely Professional University files an intellectual property right in the form of a patent entitled Weather-Adaptive Pollinator Activity Prediction Using Ensemble Learning and Real-Time Meteorological Streams, including the names of Aarav Kashyap Singh and Jai Dev Meena as inventors."), body("Lovely Professional University shall not provide financial assistance with respect to the said intellectual property right, nor shall it raise any objection at any stage with respect to filing, commercialization, or exploitation of the said patent."), spacer(6), body("Authorised Signatory: ______________________________", { center: true }), divider(NAVY), body("End of Invention Disclosure Form", { center: true })
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(DOCX_OUT, buffer);
  console.log(DOCX_OUT);
}).catch(e => {
  console.error(e);
  process.exit(1);
});
