const $ = id => document.getElementById(id);
let catalog, game, position, cursor = 0, selected = null, flipped = false;
let view = 'original', revealed = {played:false, best:false}, line = null, step = 0, busy = false;
let epoch = 0;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
  return data;
}
function fail(error) { $('error').textContent = error.message; $('error').hidden = false; }
function clearError() { $('error').hidden = true; }
function setBusy(value) {
  busy = value;
  document.querySelectorAll('button, select, input').forEach(el => el.disabled = value);
  $('board').setAttribute('aria-busy', String(value));
  if (!value && game) {
    $('previous').disabled = cursor === 0;
    $('next').disabled = cursor === game.positions.length - 1;
    $('line-back').disabled = !line || step === 0;
    $('line-next').disabled = !line || step === line.moves.length;
    $('move-input').disabled = view === 'continuation';
    $('move-form').querySelector('button').disabled = view === 'continuation';
  }
}
function draw(svg) {
  $('board').innerHTML = svg;
  $('board').querySelectorAll('.square').forEach(square => {
    const name = [...square.classList].find(c => /^[a-h][1-8]$/.test(c));
    if (!name) return;
    square.dataset.square = name;
    square.setAttribute('tabindex', '0');
    square.setAttribute('role', 'button');
    square.setAttribute('aria-label', `Square ${name}`);
    square.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); choose(name);}
    });
  });
}
async function load() {
  const token = ++epoch;
  clearError(); setBusy(true);
  try {
    const result = await api(`/api/positions/${game.positions[cursor]}?flip=${+flipped}`);
    if (token !== epoch) return;
    position = result; selected = null; view = 'original'; revealed = {played:false,best:false}; line = null; step = 0;
    draw(position.board);
    $('turn').textContent = `${position.color} to move`;
    $('date').textContent = position.date.replaceAll('.', ' · ');
    $('result').textContent = `Result ${position.result}`;
    $('progress').textContent = `Position ${cursor+1} of ${game.positions.length}`;
    $('move-number').textContent = `Move ${position.move_number}`;
    $('progress-bar').style.width = `${(cursor+1)/game.positions.length*100}%`;
    $('lesson-title').textContent = 'What would you play?';
    $('lesson-text').textContent = 'What changed after your opponent’s move? Look for checks, captures and threats.';
    $('feedback').textContent = ''; $('move-input').value = '';
    $('comparison').hidden = true; $('line').hidden = true;
    $('board-caption').textContent = 'Click a piece, then its destination.';
  } catch (error) {fail(error);} finally {if (token === epoch) setBusy(false);}
}
async function renderBoard() {
  const data = await api(`/api/positions/${position.id}/board?view=${view}&step=${step}&flip=${+flipped}`);
  draw(data.board); selected = null;
  $('turn').textContent = `${data.turn} to move`;
}
async function choose(square) {
  if (busy || !position || view === 'continuation') return;
  if (!selected || position.legal_moves.some(m => m.startsWith(square))) {
    selected = square;
    $('board').querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
    $('board').querySelector(`[data-square="${square}"]`)?.classList.add('selected');
    $('board-caption').textContent = `Selected ${square}. Choose a destination.`;
    return;
  }
  let move = selected + square;
  const promotions = position.legal_moves.filter(m => m.startsWith(move) && m.length === 5);
  if (promotions.length) {
    const piece = window.prompt('Promote to: q (queen), r (rook), b (bishop), n (knight)', 'q');
    if (piece === null) return;
    move += piece.trim().toLowerCase();
  }
  $('move-input').value = move;
  selected = null;
  await attempt(move);
}
async function attempt(move) {
  clearError(); setBusy(true);
  try {
    const data = await api(`/api/positions/${position.id}/try`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({move})});
    $('feedback').textContent = data.matches_best ? `${data.san} matches the saved best move. Nicely spotted!` : `${data.san} is legal. It differs from the saved best move; reveal it to compare. This does not necessarily mean your move is bad.`;
    $('move-input').value = data.san;
    $('board-caption').textContent = `Your candidate: ${data.san}`;
  } catch (error) {fail(error);} finally {setBusy(false);}
}
async function reveal(which) {
  clearError(); setBusy(true);
  try {
    revealed[which] = true;
    view = revealed.played && revealed.best ? 'both' : which;
    await renderBoard();
    $('line').hidden = true;
    $('comparison').hidden = false;
    $('played-value').textContent = revealed.played ? position.played : '—';
    $('best-value').textContent = revealed.best ? position.best : '—';
    $('loss').textContent = `${position.classification} · Saved evaluation loss ${position.loss.toFixed(2)} pawns`;
    $('lesson-title').textContent = which === 'best' ? 'Compare the possibilities.' : 'Your original decision.';
    $('lesson-text').textContent = which === 'best' ? 'What does this move defend, attack or threaten? Explore the engine line to see what follows.' : 'Think about what you noticed during the game. What might you have missed?';
    $('board-caption').textContent = 'Orange: your move · Green: saved best move';
  } catch (error) {fail(error);} finally {setBusy(false);}
}
async function explore() {
  clearError(); setBusy(true); $('continuation').textContent = 'Calculating continuation…';
  try {
    line = await api(`/api/positions/${position.id}/continuation`, {method:'POST'});
    view = 'continuation'; step = 0;
    await renderBoard();
    $('line').hidden = false;
    $('lesson-title').textContent = 'Follow the idea.';
    $('lesson-text').textContent = 'Step through the engine line. After each move, ask what changed.';
    updateLine();
  } catch (error) {fail(error);} finally {setBusy(false); $('continuation').textContent = 'Explore engine continuation →';}
}
function updateLine() {
  $('line-label').textContent = step === 0 ? `Line ready · depth ${line.depth} · ${line.moves.length} half-moves` : `Step ${step} of ${line.moves.length}: ${line.moves.slice(0,step).map(m=>m.san).join('  →  ')}`;
  $('board-caption').textContent = step === line.moves.length ? 'End of continuation.' : 'Purple: latest engine move';
}
async function advance(delta) {
  clearError(); setBusy(true);
  const old = step;
  try {step += delta; await renderBoard(); updateLine();}
  catch (error) {step = old; fail(error);} finally {setBusy(false);}
}
$('board').addEventListener('click', event => {
  const square = event.target.closest('[data-square]');
  if (square) choose(square.dataset.square);
});
$('move-form').addEventListener('submit', e => {e.preventDefault(); if (!busy) attempt($('move-input').value);});
$('played').onclick = () => reveal('played');
$('best').onclick = () => reveal('best');
$('continuation').onclick = explore;
$('line-back').onclick = () => advance(-1);
$('line-next').onclick = () => advance(1);
$('reset').onclick = load;
$('previous').onclick = () => {cursor--; load();};
$('next').onclick = () => {cursor++; load();};
$('game').onchange = () => {game = catalog.games.find(g=>g.id === $('game').value); cursor=0; load();};
$('flip').onclick = async () => {clearError(); setBusy(true); flipped = !flipped; try {await renderBoard();} catch(error) {flipped = !flipped; fail(error);} finally {setBusy(false);}};
(async () => {
  setBusy(true);
  try {
    catalog = await api('/api/positions');
    $('position-count').textContent = catalog.count;
    $('dataset-note').textContent = catalog.excluded_identical_moves ? `${catalog.excluded_identical_moves} identical-move score artifacts excluded` : '';
    if (!catalog.games.length) throw new Error('No training positions found in the saved analysis.');
    catalog.games.forEach(g => {const option = document.createElement('option'); option.value = g.id; option.textContent = `${g.white} vs ${g.black} · ${g.date}`; $('game').append(option);});
    game = catalog.games[0]; await load();
  } catch(error) {fail(error);}
})();
