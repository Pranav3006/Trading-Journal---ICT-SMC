from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import base64, os, json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import anthropic

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///journal.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db = SQLAlchemy(app)

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    instrument = db.Column(db.String(20), default='MNQ')
    session = db.Column(db.String(20), default='New York')
    direction = db.Column(db.String(10), default='Long')
    setup = db.Column(db.String(50), default='OB Retest')
    entry = db.Column(db.Float)
    sl = db.Column(db.Float)
    tp = db.Column(db.Float)
    contracts = db.Column(db.Integer, default=1)
    result = db.Column(db.String(20), default='Win')
    pnl = db.Column(db.Float, default=0)
    emotion = db.Column(db.String(30), default='Neutral')
    mistakes = db.Column(db.Text, default='')
    notes = db.Column(db.Text, default='')
    ai_analysis = db.Column(db.Text, default='')
    chart_image = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'date': self.date, 'instrument': self.instrument,
            'session': self.session, 'direction': self.direction, 'setup': self.setup,
            'entry': self.entry, 'sl': self.sl, 'tp': self.tp, 'contracts': self.contracts,
            'result': self.result, 'pnl': self.pnl, 'emotion': self.emotion,
            'mistakes': self.mistakes, 'notes': self.notes, 'ai_analysis': self.ai_analysis,
            'chart_image': self.chart_image,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trades', methods=['GET'])
def get_trades():
    trades = Trade.query.order_by(Trade.created_at.desc()).all()
    return jsonify([t.to_dict() for t in trades])

@app.route('/api/trades', methods=['POST'])
def add_trade():
    d = request.json
    trade = Trade(
        date=d.get('date', datetime.now().strftime('%Y-%m-%d')),
        instrument=d.get('instrument', 'MNQ'),
        session=d.get('session', 'New York'),
        direction=d.get('direction', 'Long'),
        setup=d.get('setup', 'OB Retest'),
        entry=float(d.get('entry', 0) or 0),
        sl=float(d.get('sl', 0) or 0),
        tp=float(d.get('tp', 0) or 0),
        contracts=int(d.get('contracts', 1) or 1),
        result=d.get('result', 'Win'),
        pnl=abs(float(d.get('pnl', 0) or 0)) * (-1 if d.get('result') == 'Loss' else 1),
        emotion=d.get('emotion', 'Neutral'),
        mistakes=d.get('mistakes', ''),
        notes=d.get('notes', ''),
        ai_analysis=d.get('ai_analysis', ''),
        chart_image=d.get('chart_image', '')
    )
    db.session.add(trade)
    db.session.commit()
    return jsonify(trade.to_dict()), 201

@app.route('/api/trades/<int:trade_id>', methods=['PUT'])
def update_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    d = request.json
    for field in ['date','instrument','session','direction','setup','result','emotion','mistakes','notes','ai_analysis','chart_image']:
        if field in d: setattr(trade, field, d[field])
    for field in ['entry','sl','tp']:
        if field in d: setattr(trade, field, float(d[field] or 0))
    if 'pnl' in d:
        result = d.get('result', trade.result)
        trade.pnl = abs(float(d['pnl'] or 0)) * (-1 if result == 'Loss' else 1)
    if 'contracts' in d: trade.contracts = int(d['contracts'] or 1)
    db.session.commit()
    return jsonify(trade.to_dict())

@app.route('/api/trades/<int:trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    db.session.delete(trade)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/analyze', methods=['POST'])
def analyze_trade():
    d = request.json
    api_key = d.get('api_key', '')
    if not api_key:
        return jsonify({'error': 'API key required'}), 400

    prompt = f"""You are an ICT/Smart Money trading coach. Analyze this trade and give direct feedback in Hinglish (Hindi+English mix):

Instrument: {d.get('instrument')} | Session: {d.get('session')} | Direction: {d.get('direction')}
Entry: {d.get('entry')} | SL: {d.get('sl')} | TP: {d.get('tp', 'Not set')}
Result: {d.get('result')} | P&L: ${d.get('pnl')} | Contracts: {d.get('contracts')}
Setup: {d.get('setup')} | Emotion: {d.get('emotion')}
Mistakes: {d.get('mistakes') or 'None noted'}
Notes: {d.get('notes') or 'None'}

Give feedback on: 1) Setup quality? 2) Risk management? 3) Emotion ka impact? 4) Next time kya improve kare?
Keep it under 150 words, direct aur actionable."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        image_b64 = d.get('chart_image', '')
        if image_b64 and ',' in image_b64:
            image_data = image_b64.split(',')[1]
            media_type = 'image/jpeg'
            if 'png' in image_b64[:30]: media_type = 'image/png'
            msg = client.messages.create(
                model='claude-opus-4-6',
                max_tokens=500,
                messages=[{'role': 'user', 'content': [
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': image_data}},
                    {'type': 'text', 'text': prompt}
                ]}]
            )
        else:
            msg = client.messages.create(
                model='claude-opus-4-6',
                max_tokens=500,
                messages=[{'role': 'user', 'content': prompt}]
            )
        return jsonify({'analysis': msg.content[0].text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    trades = Trade.query.all()
    if not trades:
        return jsonify({'total': 0})
    wins = [t for t in trades if t.result == 'Win']
    losses = [t for t in trades if t.result == 'Loss']
    total_pnl = sum(t.pnl for t in trades)
    win_rate = round(len(wins) / len(trades) * 100, 1)
    avg_win = round(sum(t.pnl for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t.pnl for t in losses) / len(losses), 2) if losses else 0
    rr = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0

    setup_stats = {}
    for t in trades:
        if t.setup not in setup_stats:
            setup_stats[t.setup] = {'count': 0, 'pnl': 0, 'wins': 0}
        setup_stats[t.setup]['count'] += 1
        setup_stats[t.setup]['pnl'] += t.pnl
        if t.result == 'Win': setup_stats[t.setup]['wins'] += 1

    emotion_stats = {}
    for t in trades:
        if t.emotion not in emotion_stats:
            emotion_stats[t.emotion] = {'count': 0, 'pnl': 0}
        emotion_stats[t.emotion]['count'] += 1
        emotion_stats[t.emotion]['pnl'] += t.pnl

    session_stats = {}
    for t in trades:
        if t.session not in session_stats:
            session_stats[t.session] = {'count': 0, 'pnl': 0}
        session_stats[t.session]['count'] += 1
        session_stats[t.session]['pnl'] += t.pnl

    return jsonify({
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'total_pnl': round(total_pnl, 2), 'win_rate': win_rate,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'rr': rr,
        'setup_stats': setup_stats, 'emotion_stats': emotion_stats, 'session_stats': session_stats
    })

@app.route('/api/export/pdf', methods=['GET'])
def export_pdf():
    trades = Trade.query.order_by(Trade.date.desc()).all()
    path = '/tmp/trading_journal.pdf'
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('title', fontSize=18, fontName='Helvetica-Bold', spaceAfter=6)
    elements.append(Paragraph('Trading Journal Report', title_style))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%d %b %Y %H:%M")} | Total Trades: {len(trades)}', styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))

    total_pnl = sum(t.pnl for t in trades)
    wins = len([t for t in trades if t.result == 'Win'])
    win_rate = round(wins / len(trades) * 100, 1) if trades else 0
    summary = [['Total Trades', 'Wins', 'Losses', 'Win Rate', 'Total P&L'],
               [len(trades), wins, len(trades)-wins, f'{win_rate}%', f'${total_pnl:.2f}']]
    st = Table(summary, colWidths=[1.2*inch]*5)
    st.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8f9fa'), colors.white]),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 0.2*inch))

    headers = ['Date', 'Instr', 'Dir', 'Setup', 'Entry', 'SL', 'P&L', 'Result', 'Emotion']
    data = [headers]
    for t in trades:
        data.append([t.date, t.instrument, t.direction, t.setup[:12],
                     str(t.entry), str(t.sl), f'${t.pnl:.0f}', t.result, t.emotion])
    table = Table(data, colWidths=[0.7*inch, 0.5*inch, 0.4*inch, 1.1*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.5*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8f9fa'), colors.white]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(table)

    if any(t.notes or t.mistakes or t.ai_analysis for t in trades):
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph('Trade Notes & AI Analysis', ParagraphStyle('h2', fontSize=13, fontName='Helvetica-Bold', spaceAfter=6)))
        for t in trades:
            if t.notes or t.mistakes or t.ai_analysis:
                elements.append(Paragraph(f'{t.date} | {t.instrument} | {t.result} ${t.pnl:.0f}', ParagraphStyle('th', fontSize=10, fontName='Helvetica-Bold', spaceBefore=8)))
                if t.mistakes: elements.append(Paragraph(f'Mistakes: {t.mistakes}', styles['Normal']))
                if t.notes: elements.append(Paragraph(f'Notes: {t.notes}', styles['Normal']))
                if t.ai_analysis: elements.append(Paragraph(f'AI: {t.ai_analysis[:300]}...', styles['Normal']))

    doc.build(elements)
    return send_file(path, as_attachment=True, download_name='trading_journal.pdf')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
