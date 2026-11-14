# Sharma research dashboard

The static dashboard lives at `/sharma/`. It includes sector/category browsing,
company/ticker search, directional filters, news-source status, and the actual
initial replay results. No orders are executed and no probabilities are claimed.

Public price scores are deliberately unavailable until a suitable market-data
connection and public derived-output permissions are configured. The earlier
unofficial-cache scores remain on the private review version. Do not relabel this
state as live or infer a neutral score from an N/A tile.

The scheduled workflow refreshes GDELT metadata approximately every 15 minutes;
GitHub scheduling can be delayed. GDELT publication cadence and collection lag
make it unsuitable as a guarantee of immediate ten-minute news coverage. The
collector records actual observation times and attributes GDELT. It does not
reproduce article text or classify posts as reliable financial information.
Bluesky search may return 403; this remains an explicit unavailable state.

The GitHub Pages site cannot host the continuous price service. That requires an
always-on server/runner with a provider account. The private research repository
contains the batch Alpaca adapter, cache, causal store and validation code.
Never add account keys to this public repository or page scripts.

The initial two-session replay showed no advantage for the current formula.
Its weights are untrained and its novelty is unestablished. News tone and social
posts do not currently change price scores. More historical and prospective
observations are needed before fitting or calibrating a predictive model.
