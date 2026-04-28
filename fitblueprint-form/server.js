/**
 * iKengaFit — Pre-Fit Blueprint Backend
 *
 * Handles:
 *  1. Calendly webhook → email client the form link on booking
 *  2. Form submission → generate personalized PPTX → email to coach
 *
 * SMTP: ikengafit@gmail.com (App Password auth)
 * Notify: d.r.clary25@gmail.com
 */

const express    = require('express');
const cors       = require('cors');
const fs         = require('fs');
const path       = require('path');
const nodemailer = require('nodemailer');
const PptxGenJS  = require('pptxgenjs');
const { execFile } = require('child_process');
const QRCode     = require('qrcode');

const app  = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/generated', express.static(path.join(__dirname, 'generated')));

// Ensure required directories exist (important on fresh deploys e.g. Render)
fs.mkdirSync(path.join(__dirname, 'submissions'), { recursive: true });
fs.mkdirSync(path.join(__dirname, 'generated'),  { recursive: true });

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  // Sender Gmail + app password
  smtp: {
    user: 'ikengafit@gmail.com',
    pass: 'gyof yxtp cfew mppu'.replace(/\s/g, ''), // strip spaces
  },
  // Where completed form + PPTX emails go
  coachEmail: 'ikengafit@gmail.com',
  coachName:  'David Clary',
  // The deployed form URL — update this after hosting the backend publicly
  formUrl: process.env.FORM_URL || 'https://ikengafit-blueprint.onrender.com',
  // Calendly Fit Blueprint event type URI
  fitBlueprintEventType: 'https://api.calendly.com/event_types/305ed985-c8d8-407a-8642-35218407d007',
};

// ─── NODEMAILER TRANSPORTER ───────────────────────────────────────────────────
const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: CONFIG.smtp.user,
    pass: CONFIG.smtp.pass,
  },
});

// Verify SMTP connection on startup
transporter.verify((err, success) => {
  if (err) console.error('❌ SMTP connection failed:', err.message);
  else     console.log('✅ SMTP ready — emails will send from', CONFIG.smtp.user);
});

// ─── EMAIL HELPERS ────────────────────────────────────────────────────────────

/** Email 1: Sent to client right after they book on Calendly */
async function sendFormLinkEmail({ clientName, clientEmail, sessionDate, locationStr, cancelUrl, rescheduleUrl }) {
  const firstName = clientName.split(' ')[0];
  const isVirtual = locationStr && locationStr.startsWith('http');
  const locationDisplay = isVirtual
    ? `<a href="${locationStr}" style="color:#028381;">Join virtual session</a>`
    : `<span style="color:#E8E5E0;">${locationStr || '1140 3rd St NE, Washington, DC'}</span>`;

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
</head>
<body style="margin:0;padding:0;background:#111110;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#111110;padding:40px 20px;">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#1A1917;border-radius:12px;overflow:hidden;border:1px solid #2C2B29;">

        <!-- Header bar -->
        <tr><td style="background:#028381;padding:0;line-height:0;">
          <div style="height:4px;background:linear-gradient(90deg,#028381,#8A2C0E,#028381);"></div>
        </td></tr>

        <!-- Logo row -->
        <tr><td style="padding:28px 36px 0;background:#151414;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:20px;font-weight:800;color:#FFFFFF;letter-spacing:0.02em;">
              &#9644; iKengaFit
            </td>
            <td style="padding-left:12px;">
              <span style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#028381;border:1px solid #028381;padding:3px 8px;border-radius:100px;">Fit Blueprint</span>
            </td>
          </tr></table>
        </td></tr>

        <!-- Hero -->
        <tr><td style="padding:24px 36px 28px;background:#151414;border-bottom:1px solid #2C2B29;">
          <p style="margin:0 0 8px;font-size:12px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#028381;">Your session is confirmed</p>
          <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#FFFFFF;line-height:1.15;">
            You're booked, ${firstName}
          </h1>
          <p style="margin:0;font-size:15px;color:#8A8784;line-height:1.7;">
            Your Fit Blueprint session with Coach David Clary is confirmed. See the details below and complete your Pre-Fit Blueprint before we meet.
          </p>
        </td></tr>

        <!-- Booking details card -->
        <tr><td style="padding:28px 36px 8px;">
          <div style="background:#211F1D;border-radius:8px;overflow:hidden;border:1px solid #2C2B29;">
            <div style="background:#028381;padding:10px 20px;">
              <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#FFFFFF;">Session Details</p>
            </div>
            <table cellpadding="0" cellspacing="0" width="100%" style="padding:4px 0;">
              <tr>
                <td style="padding:12px 20px;border-bottom:1px solid #2C2B29;">
                  <p style="margin:0 0 3px;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5A5856;">Event</p>
                  <p style="margin:0;font-size:14px;font-weight:700;color:#E8E5E0;">Fit Blueprint Session</p>
                </td>
              </tr>
              <tr>
                <td style="padding:12px 20px;border-bottom:1px solid #2C2B29;">
                  <p style="margin:0 0 3px;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5A5856;">Date &amp; Time</p>
                  <p style="margin:0;font-size:14px;font-weight:700;color:#E8E5E0;">${sessionDate || 'See your calendar invite'}</p>
                </td>
              </tr>
              <tr>
                <td style="padding:12px 20px;border-bottom:1px solid #2C2B29;">
                  <p style="margin:0 0 3px;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5A5856;">Location</p>
                  <p style="margin:0;font-size:14px;font-weight:700;">${locationDisplay}</p>
                </td>
              </tr>
              <tr>
                <td style="padding:12px 20px;">
                  <p style="margin:0 0 3px;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5A5856;">Coach</p>
                  <p style="margin:0;font-size:14px;font-weight:700;color:#E8E5E0;">David Clary, MS, CSCS, Pn1</p>
                </td>
              </tr>
            </table>
            ${(cancelUrl || rescheduleUrl) ? `
            <div style="padding:12px 20px;border-top:1px solid #2C2B29;">
              <table cellpadding="0" cellspacing="0"><tr>
                ${rescheduleUrl ? `<td style="padding-right:16px;"><a href="${rescheduleUrl}" style="font-size:12px;color:#028381;text-decoration:none;font-weight:600;">Reschedule</a></td>` : ''}
                ${cancelUrl ? `<td><a href="${cancelUrl}" style="font-size:12px;color:#5A5856;text-decoration:none;">Cancel</a></td>` : ''}
              </tr></table>
            </div>` : ''}
          </div>
        </td></tr>

        <!-- CTA -->
        <tr><td style="padding:24px 36px 8px;">
          <p style="margin:0 0 8px;font-size:16px;font-weight:700;color:#FFFFFF;">One thing to do before we meet</p>
          <p style="margin:0 0 24px;font-size:14px;color:#8A8784;line-height:1.6;">
            Complete your Pre-Fit Blueprint — a 5-minute questionnaire that lets Coach Clary build your personalized coaching proposal before the session, so we spend our time on strategy, not paperwork.
          </p>
          <table cellpadding="0" cellspacing="0"><tr><td>
            <a href="${CONFIG.formUrl}" style="display:inline-block;background:#028381;color:#FFFFFF;font-size:15px;font-weight:700;text-decoration:none;padding:14px 28px;border-radius:6px;letter-spacing:0.01em;">
              Complete My Pre-Fit Blueprint &rarr;
            </a>
          </td></tr></table>
          <p style="margin:16px 0 0;font-size:12px;color:#5A5856;">
            Or copy this link: <a href="${CONFIG.formUrl}" style="color:#028381;">${CONFIG.formUrl}</a>
          </p>
        </td></tr>

        <!-- What to expect -->
        <tr><td style="padding:20px 36px 28px;">
          <div style="background:#211F1D;border-radius:8px;padding:20px;border:1px solid #2C2B29;">
            <p style="margin:0 0 12px;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5A5856;">What to expect</p>
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr><td style="padding:6px 0;font-size:13px;color:#8A8784;">&#10003;&nbsp;&nbsp;Fill out your goals, fitness background &amp; schedule</td></tr>
              <tr><td style="padding:6px 0;font-size:13px;color:#8A8784;">&#10003;&nbsp;&nbsp;Select the package that fits your timeline</td></tr>
              <tr><td style="padding:6px 0;font-size:13px;color:#8A8784;">&#10003;&nbsp;&nbsp;Your personalized proposal is auto-generated</td></tr>
              <tr><td style="padding:6px 0;font-size:13px;color:#8A8784;">&#10003;&nbsp;&nbsp;Coach Clary reviews it before your session</td></tr>
            </table>
          </div>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 36px;border-top:1px solid #2C2B29;text-align:center;">
          <p style="margin:0 0 4px;font-size:12px;color:#5A5856;font-style:italic;">Find Your Place of Strength™</p>
          <p style="margin:0;font-size:11px;color:#3A3836;">
            iKengaFit · Washington, DC &amp; Virtual Nationwide ·
            <a href="https://www.ikengafit.com" style="color:#028381;">ikengafit.com</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;

  await transporter.sendMail({
    from:    `"Coach David Clary · iKengaFit" <${CONFIG.smtp.user}>`,
    to:      `"${clientName}" <${clientEmail}>`,
    subject: `You're confirmed for your Fit Blueprint, ${firstName} — one thing to do before we meet`,
    html,
    text: `Hi ${firstName},\n\nYour Fit Blueprint session is confirmed!\n\nDate & Time: ${sessionDate || 'See your calendar invite'}\nLocation: ${locationStr || '1140 3rd St NE, Washington, DC'}\nCoach: David Clary, MS, CSCS, Pn1\n${rescheduleUrl ? '\nReschedule: ' + rescheduleUrl : ''}${cancelUrl ? '\nCancel: ' + cancelUrl : ''}\n\nBefore we meet, please complete your Pre-Fit Blueprint questionnaire (5 min) so Coach Clary can build your personalized proposal before the session:\n${CONFIG.formUrl}\n\nSee you soon,\nCoach David Clary\niKengaFit`,
  });

  console.log(`✅ Form link email sent to ${clientEmail}`);
}

/**
 * Generate a PDF receipt by calling generate_receipt.py as a subprocess.
 * Returns the path to the generated PDF, or null if generation fails.
 */
function generateReceipt(submissionPath, receiptPath) {
  return new Promise((resolve) => {
    const scriptPath = path.join(__dirname, 'generate_receipt.py');
    execFile('python3', [scriptPath, submissionPath, receiptPath], { timeout: 30000 }, (err, stdout, stderr) => {
      if (err) {
        console.error('⚠️  Receipt generation failed:', err.message, stderr);
        resolve(null); // non-fatal — PPTX still sends
      } else {
        console.log('✅ Receipt PDF generated:', receiptPath);
        resolve(receiptPath);
      }
    });
  });
}

/** Email 2: Sent to coach after client submits the form, with PPTX + Receipt attached */
async function sendPptxToCoach({ clientName, clientEmail, filePath, fileName, receiptPath, receiptFileName, data }) {
  const firstName = clientName.split(' ')[0];
  const fieldsHtml = [
    ['Primary Goal',         data.primaryGoal],
    ['Fitness Level',        data.fitnessLevel],
    ['Training History',     data.trainingHistory],
    ['Availability',         data.availability],
    ['Key Focus Areas',      data.focusAreas],
    ['Recommended Package',  data.recommendedPkg],
    ['Preferred Mode',       data.preferredMode],
    ['Motivation',           data.motivation],
    ['Past Barriers',        data.barriers],
    ['Injuries / Limits',    data.injuries],
    ['Nutrition Goals',      data.nutritionGoals],
    ['Notes',                data.additionalNotes],
  ].filter(([,v]) => v && v.trim())
   .map(([label, value]) => `
    <tr>
      <td style="padding:8px 12px;font-size:12px;font-weight:700;color:#5A5856;text-transform:uppercase;letter-spacing:0.08em;width:140px;vertical-align:top;">${label}</td>
      <td style="padding:8px 12px;font-size:13px;color:#E8E5E0;line-height:1.6;">${value}</td>
    </tr>`)
   .join('');

  const html = `
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#111110;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#111110;padding:40px 20px;">
    <tr><td align="center">
      <table width="100%" style="max-width:600px;background:#1A1917;border-radius:12px;overflow:hidden;border:1px solid #2C2B29;">

        <tr><td style="height:4px;background:linear-gradient(90deg,#028381,#8A2C0E,#028381);line-height:0;font-size:0;">&nbsp;</td></tr>

        <tr><td style="padding:28px 36px 20px;background:#151414;border-bottom:1px solid #2C2B29;">
          <p style="margin:0 0 6px;font-size:12px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#028381;">New Blueprint Submission</p>
          <h1 style="margin:0;font-size:24px;font-weight:800;color:#FFFFFF;line-height:1.2;">
            ${clientName} completed their Pre-Fit Blueprint
          </h1>
          <p style="margin:8px 0 0;font-size:13px;color:#5A5856;">
            ${clientEmail} &nbsp;·&nbsp; Submitted ${new Date().toLocaleString('en-US', { timeZone: 'America/New_York', dateStyle: 'medium', timeStyle: 'short' })} ET
          </p>
        </td></tr>

        <tr><td style="padding:24px 36px;">
          <p style="margin:0 0 16px;font-size:14px;color:#8A8784;">
            The personalized coaching proposal for <strong style="color:#FFFFFF;">${firstName}</strong> is attached as a <code style="background:#211F1D;padding:2px 6px;border-radius:4px;font-size:12px;color:#028381;">.pptx</code> file. Their answers are pre-filled into the "Where You Are Today" slide.
          </p>

          <table width="100%" cellpadding="0" cellspacing="0" style="background:#211F1D;border-radius:8px;border:1px solid #2C2B29;margin-bottom:0;">
            <tr><td style="padding:12px 12px 4px;">
              <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#5A5856;">Client Responses</p>
            </td></tr>
            ${fieldsHtml}
          </table>
        </td></tr>

        <tr><td style="padding:0 36px 28px;">
          <div style="background:#1E1A17;border:1px solid #8A2C0E;border-radius:8px;padding:16px 20px;">
            <p style="margin:0;font-size:13px;color:#E8E5E0;">
              <strong style="color:#FFCAB0;">Attached:</strong> ${fileName}<br/>
              ${receiptPath ? `<strong style="color:#FFCAB0;">Also attached:</strong> ${receiptFileName} — insurance-ready PDF receipt<br/>` : ''}
              Open the deck in PowerPoint or Google Slides to review before the Fit Blueprint session.
            </p>
          </div>
        </td></tr>

        <tr><td style="padding:20px 36px;border-top:1px solid #2C2B29;text-align:center;">
          <p style="margin:0;font-size:11px;color:#3A3836;">iKengaFit · Automated via Pre-Fit Blueprint System</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;

  await transporter.sendMail({
    from:    `"iKengaFit Blueprint System" <${CONFIG.smtp.user}>`,
    to:      `"${CONFIG.coachName}" <${CONFIG.coachEmail}>`,
    replyTo: clientEmail,
    subject: `📋 New Blueprint: ${clientName} is ready for their session`,
    html,
    text: `${clientName} (${clientEmail}) completed their Pre-Fit Blueprint.\n\nGoal: ${data.primaryGoal}\nFitness Level: ${data.fitnessLevel}\nPackage: ${data.recommendedPkg}\n\nPersonalized deck attached.`,
    attachments: [
      {
        filename: fileName,
        path:     filePath,
      },
      ...(receiptPath && fs.existsSync(receiptPath) ? [{
        filename: receiptFileName || 'iKengaFit_Receipt.pdf',
        path:     receiptPath,
      }] : []),
    ],
  });

  console.log(`✅ PPTX emailed to coach for ${clientName}`);
}

// ─── BRAND / PPTX CONSTANTS ───────────────────────────────────────────────────
const TEAL      = '028381';
const TEAL_DARK = '01605F';
const CRIMSON   = '8A2C0E';
const DARK      = '151414';
const CREAM     = 'F5F1EB';
const WHITE     = 'FFFFFF';
const MUTED     = '767574';
const GRAY_DK   = '1E1E1E';
const GRAY_LT   = 'E8E4DD';

const W = 13.33, H = 7.5, M = 0.38;
const CONTENT_W = W - 2 * M;

const LOGO_LIGHT   = path.join(__dirname, 'logo_light_transparent.png');
const LH = 0.72;
const LW = LH * (1742 / 614);

function addLogoDark(s) {
  if (fs.existsSync(LOGO_LIGHT)) s.addImage({ path: LOGO_LIGHT, x: W-M-LW, y: M, w: LW, h: LH });
}
function addLogoInTealHeader(s, hdrH) {
  if (fs.existsSync(LOGO_LIGHT)) s.addImage({ path: LOGO_LIGHT, x: W-M-LW, y: (hdrH-LH)/2, w: LW, h: LH });
}
function addLogoInDarkHeader(s, hdrH) {
  if (fs.existsSync(LOGO_LIGHT)) s.addImage({ path: LOGO_LIGHT, x: W-M-LW, y: (hdrH-LH)/2, w: LW, h: LH });
}
function lbl(s, text, color, y) {
  s.addText(text.toUpperCase(), { x:M, y, w:CONTENT_W, h:0.24, fontSize:8, bold:true, color, charSpacing:3.5, fontFace:'Trebuchet MS' });
}
function rule(s, x, y, w, color=CRIMSON) {
  s.addShape('rect', { x, y, w, h:0.04, fill:{color}, line:{type:'none'} });
}

// ─── PPTX GENERATION ─────────────────────────────────────────────────────────
async function generateDeck(data) {
  const prs = new PptxGenJS();
  prs.layout = 'LAYOUT_WIDE';

  const {
    clientName='[Client Name]', primaryGoal='[Not specified]',
    fitnessLevel='[Not specified]', trainingHistory='[Not specified]',
    availability='[Not specified]', focusAreas='[Not specified]',
    recommendedPkg='To be determined',
  } = data;

  // ── SLIDE 1 — COVER ─────────────────────────────────────────────────────────
  {
    const s = prs.addSlide();
    s.background = { color: DARK };
    s.addShape('rect', {x:0,y:0,w:0.22,h:H,fill:{color:TEAL},line:{type:'none'}});
    lbl(s, 'Personalized Fitness Coaching', TEAL, M);
    s.addText('YOUR COACHING\nPACKAGE PROPOSAL', {x:M,y:0.88,w:9.2,h:2.4,fontSize:54,bold:true,color:WHITE,fontFace:'Trebuchet MS',lineSpacingMultiple:1.07});
    s.addText('Find Your Place of Strength\u2122', {x:M,y:3.42,w:8,h:0.46,fontSize:18,color:TEAL,fontFace:'Trebuchet MS',italic:true});
    rule(s,M,3.98,2.8);
    s.addText(`Prepared exclusively for ${clientName} following your iKengaFit Fitness Assessment`, {x:M,y:4.15,w:9,h:0.36,fontSize:12.5,color:'AAAAAA',fontFace:'Trebuchet MS'});
    s.addText('iKengaFit', {x:M,y:6.68,w:3.5,h:0.44,fontSize:20,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    addLogoDark(s);
    const bW=3.3,bH=1.9,bX=W-M-bW,bY=H-M-bH;
    s.addShape('rect',{x:bX,y:bY,w:bW,h:bH,fill:{color:CRIMSON},line:{type:'none'}});
    s.addText('Washington, DC\n& Virtual Nationwide',{x:bX+0.18,y:bY+0.22,w:bW-0.36,h:0.88,fontSize:12,bold:true,color:WHITE,align:'center',fontFace:'Trebuchet MS',lineSpacingMultiple:1.3});
    s.addText('ikengafit.com',{x:bX+0.18,y:bY+1.2,w:bW-0.36,h:0.34,fontSize:11,color:'FFCAB0',align:'center',fontFace:'Trebuchet MS'});
  }

  // ── SLIDE 2 — TRAINER ────────────────────────────────────────────────────────
  {
    const s = prs.addSlide();
    s.background = { color: CREAM };
    const hH=1.55;
    s.addShape('rect',{x:0,y:0,w:W,h:hH,fill:{color:TEAL},line:{type:'none'}});
    addLogoInTealHeader(s,hH);
    s.addText('ABOUT iKENGAFIT',{x:M,y:0.22,w:8.5,h:0.26,fontSize:9,bold:true,color:WHITE,charSpacing:4,fontFace:'Trebuchet MS'});
    s.addText('Your Trainer & Credentials',{x:M,y:0.56,w:8.5,h:0.72,fontSize:30,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    const lX=M,lW=5.9,cTop=hH+0.22;
    s.addText('Who We Are',{x:lX,y:cTop,w:lW,h:0.4,fontSize:18,bold:true,color:TEAL,fontFace:'Trebuchet MS'});
    rule(s,lX,cTop+0.46,1.2);
    s.addText('iKengaFit is a Washington, DC-based personal training and coaching practice serving clients in-person in the NOMA area and virtually nationwide. Every program is built around you — your goals, your schedule, your life.',{x:lX,y:cTop+0.6,w:lW,h:1.48,fontSize:13,color:DARK,fontFace:'Trebuchet MS',lineSpacingMultiple:1.5});
    const bsY=cTop+2.26;
    s.addShape('rect',{x:lX,y:bsY,w:lW,h:0.76,fill:{color:TEAL_DARK},line:{type:'none'}});
    s.addText('"Grab YOUR health by the horns."',{x:lX+0.18,y:bsY+0.12,w:lW-0.36,h:0.52,fontSize:13.5,bold:true,color:WHITE,italic:true,fontFace:'Trebuchet MS'});
    s.addText('In-person: Washington, DC (NOMA area)\nVirtually nationwide',{x:lX,y:bsY+0.96,w:lW,h:0.62,fontSize:12,color:DARK,fontFace:'Trebuchet MS',lineSpacingMultiple:1.4});
    const cX=7.05,cW=W-M-cX,cY=hH+0.22,cH=H-M-cY;
    s.addShape('rect',{x:cX,y:cY,w:cW,h:cH,fill:{color:DARK},line:{type:'none'}});
    const ci=0.25;
    s.addText('MEET YOUR TRAINER',{x:cX+ci,y:cY+0.2,w:cW-ci*2,h:0.24,fontSize:8,bold:true,color:TEAL,charSpacing:3,fontFace:'Trebuchet MS'});
    s.addText('David Clary',{x:cX+ci,y:cY+0.5,w:cW-ci*2,h:0.55,fontSize:28,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    s.addText('BS, MS, CSCS, Pn1',{x:cX+ci,y:cY+1.1,w:cW-ci*2,h:0.3,fontSize:12.5,color:TEAL,italic:true,fontFace:'Trebuchet MS'});
    rule(s,cX+ci,cY+1.5,1.6);
    [['M.S.','Clinical Exercise Science — Liberty University'],['B.S.','Human Performance — Howard University'],['CSCS','Certified Strength & Conditioning Specialist'],['Pn1','Precision Nutrition Coach, Level 1'],['NASM','Nationally Certified Personal Trainer'],['Bio.','Dartfish Biomechanical Analysis Technician']].forEach(([a,d],i)=>{
      const ry=cY+1.72+i*0.48;
      s.addText(a,{x:cX+ci,y:ry,w:0.68,h:0.36,fontSize:10,bold:true,color:TEAL,fontFace:'Trebuchet MS'});
      s.addText(d,{x:cX+ci+0.75,y:ry,w:cW-ci*2-0.75,h:0.36,fontSize:10,color:'CCCCCC',fontFace:'Trebuchet MS'});
    });
    s.addText('Human Performance Expert  ·  DMV Area',{x:cX+ci,y:cY+cH-0.36,w:cW-ci*2,h:0.28,fontSize:9,color:MUTED,fontFace:'Trebuchet MS'});
  }

  // ── SLIDE 3 — ASSESSMENT RECAP (CLIENT DATA) ──────────────────────────────
  {
    const s = prs.addSlide();
    s.background = { color: DARK };
    s.addShape('rect',{x:0,y:0,w:0.22,h:H,fill:{color:TEAL},line:{type:'none'}});
    addLogoDark(s);
    lbl(s,'Your Fitness Assessment Recap','AAAAAA',M);
    s.addText('Where You Are Today',{x:M,y:0.7,w:CONTENT_W,h:0.72,fontSize:38,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    rule(s,M,1.5,2.2);
    s.addText(`Assessment summary for ${clientName}:`,{x:M,y:1.64,w:CONTENT_W-0.5,h:0.34,fontSize:12,color:'AAAAAA',fontFace:'Trebuchet MS'});

    const gStartY=2.1,gEndY=H-M-0.25,tGridH=gEndY-gStartY,rowGap=0.2,rowH=(tGridH-rowGap)/2;
    const gStartX=M,gEndX=W-M,colGap=0.2,colW=(gEndX-gStartX-2*colGap)/3;

    const boxes=[
      ['Primary Goal',        primaryGoal],
      ['Fitness Level',       fitnessLevel],
      ['Training History',    trainingHistory],
      ['Availability',        availability],
      ['Key Focus Areas',     focusAreas],
      ['Recommended Package', recommendedPkg],
    ];
    boxes.forEach(([l,v],idx)=>{
      const col=idx%3,row=Math.floor(idx/3);
      const bx=gStartX+col*(colW+colGap),by=gStartY+row*(rowH+rowGap);
      s.addShape('rect',{x:bx,y:by,w:colW,h:rowH,fill:{color:GRAY_DK},line:{color:TEAL,pt:1}});
      s.addText(l.toUpperCase(),{x:bx+0.22,y:by+0.22,w:colW-0.44,h:0.26,fontSize:8,bold:true,color:TEAL,charSpacing:2,fontFace:'Trebuchet MS'});
      s.addText(v,{x:bx+0.22,y:by+0.62,w:colW-0.44,h:rowH-0.88,fontSize:14,bold:true,color:WHITE,fontFace:'Trebuchet MS',lineSpacingMultiple:1.3});
    });
  }

  // ── SLIDES 4–8 (benefits, comparison, CTA, closing) ────────────────────
  // NOTE: The old "Choose the package" slide has been removed.
  // Slide 4 is now Benefits, Slide 5 Comparison, Slide 6 Pricing CTA, Slide 7 Closing.

  // Benefits slide
  {
    const s=prs.addSlide();
    s.background={color:DARK};
    s.addShape('rect',{x:0,y:0,w:0.22,h:H,fill:{color:TEAL},line:{type:'none'}});
    addLogoDark(s);
    lbl(s,'What You Get With Every Package','AAAAAA',M);
    s.addText('Built for You. Built to Perform.',{x:M,y:0.7,w:CONTENT_W,h:0.72,fontSize:38,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    rule(s,M,1.5,2.2);
    const bens=[['01','Customized Workouts','Every session is designed around your goals, movement patterns, and fitness level — no cookie-cutter plans.'],['02','Expert Coaching & Feedback','Real-time instruction and corrections from a CSCS-certified trainer with an M.S. in Clinical Exercise Science.'],['03','Virtual or In-Person','Train in-person in Washington, DC (NOMA area) or virtually from anywhere in the country — same quality.'],['04','Performance Tracking','App access to track goals and performance metrics so you can measure and visualize your progress over time.'],['05','Flexible Payment','One-time package purchases with no monthly commitment. Split-payment available on 12- and 24-session packages.'],['06','A Clear Path Forward','Standard packages are a strong starting point — many clients upgrade to Elite Coaching after their first package.']];
    const bTop=1.68,bBot=H-M-0.25,tBH=bBot-bTop,rH=tBH/3,bLeft=M,bRight=W-M,cg2=0.55,bCW=(bRight-bLeft-cg2)/2;
    bens.forEach(([n,t,b],i)=>{
      const col=i%2,row=Math.floor(i/2),bx=bLeft+col*(bCW+cg2),by=bTop+row*rH;
      s.addText(n,{x:bx,y:by+0.08,w:0.58,h:0.44,fontSize:20,bold:true,color:TEAL,fontFace:'Trebuchet MS'});
      s.addText(t,{x:bx+0.64,y:by+0.1,w:bCW-0.64,h:0.36,fontSize:13.5,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
      s.addText(b,{x:bx+0.64,y:by+0.5,w:bCW-0.64,h:rH-0.6,fontSize:11,color:'AAAAAA',fontFace:'Trebuchet MS',lineSpacingMultiple:1.38});
    });
  }

  // Comparison slide
  {
    const s=prs.addSlide();
    s.background={color:CREAM};
    const hH=1.55;
    s.addShape('rect',{x:0,y:0,w:W,h:hH,fill:{color:DARK},line:{type:'none'}});
    addLogoInDarkHeader(s,hH);
    s.addText('COACHING COMPARISON',{x:M,y:0.22,w:8.5,h:0.26,fontSize:9,bold:true,color:TEAL,charSpacing:4,fontFace:'Trebuchet MS'});
    s.addText('Standard Coaching vs. Elite Coaching',{x:M,y:0.56,w:8.5,h:0.72,fontSize:28,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    const tL=M,tR=W-M,tW=tR-tL,cWs=[tW*0.26,tW*0.26,tW*0.24,tW*0.24],cXs=[tL,tL+cWs[0],tL+cWs[0]+cWs[1],tL+cWs[0]+cWs[1]+cWs[2]];
    const tHY=hH+0.12,tHH=0.5;
    s.addShape('rect',{x:tL,y:tHY,w:tW,h:tHH,fill:{color:TEAL},line:{type:'none'}});
    ['Feature','Standard Coaching','Elite — Precision (2x/wk)','Elite — Signature (3x/wk)'].forEach((h,i)=>s.addText(h,{x:cXs[i]+0.1,y:tHY+0.06,w:cWs[i]-0.12,h:tHH-0.08,fontSize:10,bold:true,color:WHITE,align:i===0?'left':'center',fontFace:'Trebuchet MS'}));
    const rows=[['Coaching Model','Session-based','Monthly program','Monthly program'],['Personalized Plan','\u2713','\u2713','\u2713'],['Ongoing Accountability','\u2717','\u2713','\u2713'],['Weekly Check-Ins','\u2717','\u2713','\u2713'],['Habit & Nutrition Guidance','\u2717','\u2713','\u2713'],['Progress Reviews','\u2717','\u2713','\u2713'],['Application Required','Not required','Required','Required'],['Schedule Flexibility','High','Moderate','Moderate'],['Investment','From $270','$1,000/mo','$1,500/mo']];
    const tDT=tHY+tHH,tDB=H-M-0.38,rH2=(tDB-tDT)/rows.length;
    rows.forEach((row,ri)=>{
      const ry=tDT+ri*rH2,bg=ri%2===0?GRAY_LT:CREAM;
      s.addShape('rect',{x:tL,y:ry,w:tW,h:rH2,fill:{color:bg},line:{type:'none'}});
      s.addShape('rect',{x:cXs[1],y:ry,w:cWs[1],h:rH2,fill:{color:'D8ECEB'},line:{type:'none'}});
      row.forEach((cell,ci)=>{
        const ic=cell==='\u2713',ix=cell==='\u2717';
        const cc=ic?(ci===1?TEAL_DARK:'5A9EA0'):ix?'888888':DARK;
        s.addText(cell,{x:cXs[ci]+0.1,y:ry+0.04,w:cWs[ci]-0.12,h:rH2-0.06,fontSize:ci===0?10.5:12,bold:ic&&ci===1,color:cc,align:ci===0?'left':'center',fontFace:'Trebuchet MS',valign:'middle'});
      });
    });
    s.addText('Elite Coaching requires an application and a 3-month minimum commitment.',{x:tL,y:tDB+0.06,w:10,h:0.28,fontSize:9.5,color:DARK,italic:true,fontFace:'Trebuchet MS'});
  }

  // Pricing CTA slide — with per-package QR codes + Elite QR in red section
  await (async () => {
    const s=prs.addSlide();
    s.background={color:TEAL};
    s.addShape('rect',{x:0,y:0,w:0.22,h:H,fill:{color:TEAL_DARK},line:{type:'none'}});
    if(fs.existsSync(LOGO_LIGHT)) s.addImage({path:LOGO_LIGHT,x:W-M-LW,y:M,w:LW,h:LH});
    lbl(s,'Pricing & Next Steps',WHITE,M);
    s.addText("Ready to Start? Let's Get to Work.",{x:M,y:0.7,w:CONTENT_W,h:0.72,fontSize:36,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    rule(s,M,1.5,2.8,CRIMSON);

    const STANDARD_URL = 'https://www.ikengafit.com/standardcoaching';
    const ELITE_URL    = 'https://www.ikengafit.com/elitecoaching';

    // Generate QR code PNGs to temp files
    const qrStdPath  = `/tmp/qr_standard.png`;
    const qrElitePath= `/tmp/qr_elite.png`;
    await QRCode.toFile(qrStdPath,  STANDARD_URL, {width:180,margin:1,color:{dark:'151414',light:'FFFFFF'}});
    await QRCode.toFile(qrElitePath,ELITE_URL,    {width:180,margin:1,color:{dark:'151414',light:'FFFFFF'}});

    const pD=[
      {pkg:'6 Sessions', virt:'$270',  ip:'$600',   weeks:'2–3 weeks  ·  Min 2x/week'},
      {pkg:'12 Sessions',virt:'$600',  ip:'$1,080', weeks:'4–6 weeks  ·  Min 2x/week'},
      {pkg:'24 Sessions',virt:'$1,080',ip:'$1,920', weeks:'8–12 weeks  ·  Min 2x/week'},
    ];
    const ctaH=1.62,ctaY=H-M-ctaH,cTop2=1.68,cHp=ctaY-0.22-cTop2,cg2=0.25,cWp=(CONTENT_W-2*cg2)/3;
    const qrSize=0.9; // inches

    pD.forEach((p,i)=>{
      const bx=M+i*(cWp+cg2),by=cTop2;
      s.addShape('rect',{x:bx,y:by,w:cWp,h:cHp,fill:{color:TEAL_DARK},line:{type:'none'}});
      s.addText(p.pkg,{x:bx+0.2,y:by+0.2,w:cWp-0.4,h:0.42,fontSize:16,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
      s.addText(p.weeks,{x:bx+0.2,y:by+0.66,w:cWp-0.4,h:0.28,fontSize:9.5,color:'CCE8E8',fontFace:'Trebuchet MS'});
      s.addShape('rect',{x:bx+0.2,y:by+1.04,w:cWp-0.4,h:0.03,fill:{color:'035E5D'},line:{type:'none'}});
      const pCW=(cWp-0.4)/2-0.08,pC2X=bx+0.2+pCW+0.16;
      s.addText('VIRTUAL',{x:bx+0.2,y:by+1.18,w:pCW,h:0.22,fontSize:7.5,bold:true,color:'CCE8E8',charSpacing:1,fontFace:'Trebuchet MS'});
      s.addText(p.virt,{x:bx+0.2,y:by+1.42,w:pCW,h:0.64,fontSize:30,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
      s.addText('IN-PERSON',{x:pC2X,y:by+1.18,w:pCW,h:0.22,fontSize:7.5,bold:true,color:'FFCAB0',charSpacing:1,fontFace:'Trebuchet MS'});
      s.addText(p.ip,{x:pC2X,y:by+1.42,w:pCW,h:0.64,fontSize:30,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
      // QR code + tap-to-book link inside each card
      const qrX=bx+(cWp-qrSize)/2, qrY=by+cHp-qrSize-0.52;
      s.addImage({path:qrStdPath,x:qrX,y:qrY,w:qrSize,h:qrSize,hyperlink:{url:STANDARD_URL}});
      s.addText('Tap to Book',{x:bx+0.1,y:qrY+qrSize+0.02,w:cWp-0.2,h:0.28,fontSize:8.5,color:'151414',align:'center',fontFace:'Trebuchet MS',hyperlink:{url:STANDARD_URL,color:'151414'}});
    });

    // Red Elite CTA section at bottom
    s.addShape('rect',{x:M,y:ctaY,w:CONTENT_W,h:ctaH,fill:{color:CRIMSON},line:{type:'none'}});
    // Elite QR on the right side of the red section
    const eliteQrSize=1.1, eliteQrX=W-M-eliteQrSize-0.22, eliteQrY=ctaY+(ctaH-eliteQrSize)/2;
    s.addImage({path:qrElitePath,x:eliteQrX,y:eliteQrY,w:eliteQrSize,h:eliteQrSize,hyperlink:{url:ELITE_URL}});
    // Text on the left of the red section
    s.addText('Interested in Elite Coaching?',{x:M+0.25,y:ctaY+0.18,w:8.5,h:0.38,fontSize:18,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    s.addText('Apply at ikengafit.com/elitecoaching — Precision (2x/wk) $1,000/mo  ·  Signature (3x/wk) $1,500/mo',{x:M+0.25,y:ctaY+0.6,w:eliteQrX-M-0.5,h:0.32,fontSize:10,color:'FFCAB0',fontFace:'Trebuchet MS'});
    s.addText('Scan to Apply  →',{x:M+0.25,y:ctaY+0.98,w:eliteQrX-M-0.5,h:0.3,fontSize:10,bold:true,color:'151414',fontFace:'Trebuchet MS',hyperlink:{url:ELITE_URL,color:'151414'}});
    // Standard clickable link button
    const bW2=2.55,bX2=M+0.25,bY2=ctaY+1.28,bH2=0.24;
    s.addText('\u2192  Book standard packages at ikengafit.com/standardcoaching',{x:bX2,y:bY2,w:eliteQrX-M-0.5,h:bH2,fontSize:9,color:'151414',fontFace:'Trebuchet MS',hyperlink:{url:STANDARD_URL,color:'151414'}});
  })();

  // Closing slide
  {
    const s=prs.addSlide();
    s.background={color:TEAL};
    const pW=5.5;
    s.addShape('rect',{x:0,y:0,w:pW,h:H,fill:{color:DARK},line:{type:'none'}});
    const lx=M,lw=pW-M-0.3;
    s.addText('iKengaFit',{x:lx,y:0.82,w:lw,h:0.6,fontSize:32,bold:true,color:WHITE,fontFace:'Trebuchet MS'});
    rule(s,lx,1.5,1.8,CRIMSON);
    s.addText('Find Your Place of Strength\u2122',{x:lx,y:1.65,w:lw,h:0.6,fontSize:17,color:TEAL,italic:true,fontFace:'Trebuchet MS'});
    s.addText('David Clary, MS, CSCS, Pn1',{x:lx,y:2.55,w:lw,h:0.32,fontSize:11.5,color:'AAAAAA',fontFace:'Trebuchet MS'});
    s.addText('Personal Trainer & Coach',{x:lx,y:2.9,w:lw,h:0.3,fontSize:11.5,color:'AAAAAA',fontFace:'Trebuchet MS'});
    s.addText('CONTACT & LINKS',{x:lx,y:4.08,w:lw,h:0.22,fontSize:7.5,bold:true,color:TEAL,charSpacing:2.5,fontFace:'Trebuchet MS'});
    rule(s,lx,4.36,lw,TEAL);
    ['ikengafit.com','ikengafit.com/standardcoaching','Washington, DC & Virtual'].forEach((c,i)=>s.addText(c,{x:lx,y:4.52+i*0.46,w:lw,h:0.38,fontSize:11,color:TEAL,fontFace:'Trebuchet MS'}));
    if(fs.existsSync(LOGO_LIGHT)) s.addImage({path:LOGO_LIGHT,x:lx,y:H-M-LH-0.1,w:LW,h:LH});
    const rx=pW+M,rw=W-rx-M;
    s.addText('YOUR NEXT STEP',{x:rx,y:0.82,w:rw,h:0.26,fontSize:8.5,bold:true,color:TEAL_DARK,charSpacing:3.5,fontFace:'Trebuchet MS'});
    s.addText("Let's Build\nYour Strongest Self.",{x:rx,y:1.15,w:rw,h:1.95,fontSize:38,bold:true,color:WHITE,fontFace:'Trebuchet MS',lineSpacingMultiple:1.1});
    rule(s,rx,3.22,2.8,CRIMSON);
    s.addText("Your assessment is complete. Your program is ready to be built. The next step is yours — select a package, book your sessions, and let's get to work.",{x:rx,y:3.4,w:rw,h:1.2,fontSize:13,color:WHITE,fontFace:'Trebuchet MS',lineSpacingMultiple:1.5});
    const bY3=4.88,bH3=0.72;
    s.addShape('rect',{x:rx,y:bY3,w:rw,h:bH3,fill:{color:CRIMSON},line:{type:'none'}});
    s.addText('BOOK YOUR PACKAGE  \u2192',{x:rx,y:bY3,w:rw,h:bH3,fontSize:13,bold:true,color:'151414',align:'center',fontFace:'Trebuchet MS',hyperlink:{url:'https://www.ikengafit.com/standardcoaching',color:'151414'}});
    // Free week CTA
    const fwY=bY3+bH3+0.18;
    s.addShape('rect',{x:rx,y:fwY,w:rw,h:0.5,fill:{color:TEAL_DARK},line:{type:'none'}});
    s.addText('\u2728  Try 1 FREE Week of the Elite Performance System in the iKengaFit App',{x:rx+0.15,y:fwY+0.02,w:rw-0.3,h:0.46,fontSize:9.5,bold:true,color:'151414',fontFace:'Trebuchet MS',hyperlink:{url:'https://www.trainerize.me/profile/ikengafit/?planGUID=2fb410d7fbb14be099af2438ffef93ce',color:'151414'}});
    s.addText('Questions? Visit ikengafit.com or book a free Fitness Assessment.',{x:rx,y:H-M-0.38,w:rw,h:0.3,fontSize:9.5,color:DARK,fontFace:'Trebuchet MS'});
  }

  return prs;
}

// ─── API ROUTES ───────────────────────────────────────────────────────────────

app.get('/api/health', (req, res) => res.json({ ok: true, smtp: CONFIG.smtp.user }));

// ── CALENDLY WEBHOOK ─────────────────────────────────────────────────────────
// Calendly will POST here when a new Fit Blueprint booking is made
// Register this URL in Calendly Dashboard → Integrations → Webhooks
// Endpoint: https://YOUR-DOMAIN/api/calendly-webhook
app.post('/api/calendly-webhook', (req, res) => {
  // Respond to Calendly IMMEDIATELY (within ms) so it never times out on a cold start
  res.json({ received: true });

  // Process the booking asynchronously in the background
  (async () => {
  try {
    const event   = req.body;
    const payload = event.payload || event;

    console.log('📅 Calendly webhook received:', event.event);
    console.log('   Raw payload keys:', Object.keys(payload).join(', '));

    if (event.event !== 'invitee.created') {
      console.log('ℹ️  Ignored — not invitee.created');
      return;
    }

    // In real Calendly webhooks the invitee IS the payload directly.
    // payload.event is a URI string pointing to the scheduled event — NOT an object.
    // payload.event_type is NOT present on the invitee; we must fetch the scheduled event.
    const invitee       = payload;
    const clientName    = invitee.name        || 'New Client';
    const clientEmail   = invitee.email       || '';
    const cancelUrl     = invitee.cancel_url  || '';
    const rescheduleUrl = invitee.reschedule_url || '';
    const eventUri      = typeof invitee.event === 'string' ? invitee.event : '';

    if (!clientEmail) {
      console.log('⚠️  No client email — skipping.');
      return;
    }
    if (!eventUri) {
      console.log('⚠️  No event URI — skipping.');
      return;
    }

    // Fetch the scheduled event from Calendly API to get event_type + start_time + location
    const CALENDLY_PAT = process.env.CALENDLY_PAT || 'eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzc2ODA4MzU5LCJqdGkiOiI3ZjBlZDlkNS1jNzE1LTQ0NGEtOTliZS01NzY5ZjgwYzQ0YjkiLCJ1c2VyX3V1aWQiOiI2MjcwMTcyMC1mMGFjLTRjNTYtYjI0OS1kNDMzNDViNzA0OTkiLCJzY29wZSI6Imdyb3VwczpyZWFkIG9yZ2FuaXphdGlvbnM6cmVhZCBvcmdhbml6YXRpb25zOndyaXRlIHVzZXJzOnJlYWQgYXZhaWxhYmlsaXR5OnJlYWQgYXZhaWxhYmlsaXR5OndyaXRlIGV2ZW50X3R5cGVzOnJlYWQgZXZlbnRfdHlwZXM6d3JpdGUgbG9jYXRpb25zOnJlYWQgcm91dGluZ19mb3JtczpyZWFkIHNoYXJlczp3cml0ZSBzY2hlZHVsZWRfZXZlbnRzOnJlYWQgc2NoZWR1bGVkX2V2ZW50czp3cml0ZSBzY2hlZHVsaW5nX2xpbmtzOndyaXRlIGFjdGl2aXR5X2xvZzpyZWFkIGRhdGFfY29tcGxpYW5jZTp3cml0ZSBvdXRnb2luZ19jb21tdW5pY2F0aW9uczpyZWFkIHdlYmhvb2tzOnJlYWQgd2ViaG9va3M6d3JpdGUifQ.Mouh_NK5mkBip2-_RxCCgpq5qLuGKwVpwsC3lqJNtXKEgmCjaxdOFcw5fsCtSxfVOadE_fWEj1NpmTSlU5rryg';
    const evtResp = await fetch(eventUri, {
      headers: { 'Authorization': `Bearer ${CALENDLY_PAT}` }
    });
    const evtData = await evtResp.json();
    const scheduledEvent = evtData.resource || evtData;

    console.log('   Fetched event type URI:', scheduledEvent.event_type);

    // Check if this is the Fit Blueprint event type
    const eventTypeUri = scheduledEvent.event_type || '';
    const isFitBlueprint = eventTypeUri.includes('305ed985-c8d8-407a-8642-35218407d007');

    if (!isFitBlueprint) {
      console.log('ℹ️  Not Fit Blueprint — skipping. event_type:', eventTypeUri);
      return;
    }

    // Extract session details from the fetched event
    const startTime   = scheduledEvent.start_time || '';
    const sessionDate = startTime
      ? new Date(startTime).toLocaleString('en-US', { timeZone: 'America/New_York', dateStyle: 'full', timeStyle: 'short' })
      : null;
    const locationRaw = scheduledEvent.location || {};
    const locationStr = locationRaw.location || locationRaw.join_url || locationRaw.description || '1140 3rd St NE, Washington, DC';

    console.log(`📧 Sending form link to ${clientName} <${clientEmail}> for session ${sessionDate}`);
    await sendFormLinkEmail({ clientName, clientEmail, sessionDate, locationStr, cancelUrl, rescheduleUrl });
    console.log(`✅ Form link sent to ${clientEmail}`);

  } catch (err) {
    console.error('❌ Webhook async error:', err.message, err.stack);
  }
  })(); // end async IIFE
});

// ── FORM SUBMISSION → PPTX → EMAIL COACH ────────────────────────────────────
app.post('/api/submit', async (req, res) => {
  try {
    const data = req.body;
    const clientName = data.fullName || 'Client';

    // Map form fields to Assessment Recap boxes
    data.clientName      = clientName;
    data.primaryGoal     = data.primaryGoal     || '[Not specified]';
    data.fitnessLevel    = data.fitnessLevel     || '[Not specified]';
    data.trainingHistory = data.trainingHistory  || '[Not specified]';
    data.availability    = [data.sessionDays, data.sessionTime].filter(Boolean).join(' · ') || '[Not specified]';
    data.focusAreas      = data.focusAreas       || '[Not specified]';
    data.recommendedPkg  = data.recommendedPkg   || 'To be determined';

    // Save submission JSON
    const ts       = Date.now();
    const safeName = clientName.replace(/[^a-z0-9]/gi, '_');
    const subDir   = path.join(__dirname, 'submissions');
    const genDir   = path.join(__dirname, 'generated');
    // Guarantee directories exist at write-time (covers all hosting environments)
    fs.mkdirSync(subDir, { recursive: true });
    fs.mkdirSync(genDir, { recursive: true });
    fs.writeFileSync(
      path.join(subDir, `${safeName}_${ts}.json`),
      JSON.stringify({ ...data, submittedAt: new Date().toISOString() }, null, 2)
    );

    // Generate PPTX
    const prs      = await generateDeck(data);
    const fileName = `iKengaFit_Blueprint_${safeName}_${ts}.pptx`;
    const filePath = path.join(genDir, fileName);
    await prs.writeFile({ fileName: filePath });
    console.log(`✅ PPTX generated: ${fileName}`);

    // Convert PPTX → PDF for client download (non-fatal if LibreOffice unavailable)
    let pdfFileName = null;
    let pdfFilePath = null;
    try {
      const { execSync } = require('child_process');
      execSync(`libreoffice --headless --convert-to pdf --outdir "${genDir}" "${filePath}"`, { timeout: 60000 });
      pdfFileName = fileName.replace('.pptx', '.pdf');
      pdfFilePath = path.join(genDir, pdfFileName);
      if (!fs.existsSync(pdfFilePath)) throw new Error('PDF not found after conversion');
      console.log(`✅ PDF generated: ${pdfFileName}`);
    } catch (pdfErr) {
      console.warn('⚠️  PDF conversion failed (LibreOffice unavailable?), falling back to PPTX:', pdfErr.message);
      pdfFileName = null;
      pdfFilePath = null;
    }

    // Generate PDF receipt (non-fatal if Python fails)
    const subJsonPath    = path.join(subDir, `${safeName}_${ts}.json`);
    const receiptFileName = `iKengaFit_Receipt_${safeName}_${ts}.pdf`;
    const receiptPath    = path.join(genDir, receiptFileName);
    const receiptResult  = await generateReceipt(subJsonPath, receiptPath);

    // Email PPTX + receipt to coach
    await sendPptxToCoach({
      clientName,
      clientEmail: data.email || '',
      filePath,
      fileName,
      receiptPath:     receiptResult,
      receiptFileName,
      data,
    });

    res.json({
      success:      true,
      clientName,
      downloadUrl:  pdfFilePath ? `/generated/${pdfFileName}` : `/generated/${fileName}`,
      fileName:     pdfFilePath ? pdfFileName : fileName,
      pdfUrl:       pdfFilePath ? `/generated/${pdfFileName}` : null,
      pdfFileName:  pdfFileName || null,
    });
  } catch (err) {
    console.error('❌ Submit error:', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── SUBMISSIONS LIST ─────────────────────────────────────────────────────────
app.get('/api/submissions', (req, res) => {
  const subDir = path.join(__dirname, 'submissions');
  const files  = fs.readdirSync(subDir).filter(f => f.endsWith('.json'));
  const list   = files.map(f => {
    const d = JSON.parse(fs.readFileSync(path.join(subDir, f), 'utf8'));
    return { file: f, clientName: d.clientName || d.fullName, email: d.email, submittedAt: d.submittedAt };
  });
  res.json(list.reverse());
});

app.listen(PORT, () => {
  console.log(`\n🏋️  iKengaFit Blueprint server on port ${PORT}`);
  console.log(`📋  Form:           ${CONFIG.formUrl}`);
  console.log(`🔗  Webhook URL:    ${CONFIG.formUrl}/api/calendly-webhook`);
  console.log(`📬  PPTX emails to: ${CONFIG.coachEmail}\n`);
});
