// fixed DOM elements
const sourcesDiv = document.getElementById("sources");
const playListElem = document.getElementById("play-list");
const songListElem = document.getElementById("song-list");

// ...of the player
const audio = document.getElementById("audio-player");
const playPauseBtn = document.getElementById("play-pause");
const seekBar = document.getElementById("seek-bar");
const currentTimeElem = document.getElementById("current-time");
const totalDurationElem = document.getElementById("total-duration");

// some parameters
const seekbarResolutionHz = 10; // realistically the updates come at about 6hz - anything above makes no difference

// some global state
var currentPlaylist = null;
var currentRootSong = null;
var currentSongInPlayer = null;
var currentTreeChildren = null;

async function fetchSources() {
  const res = await fetch("/sources");
  const sources = await res.json();

  sources.forEach(name => {
    const btn = document.createElement("button");
    // btn.textContent = `Update from ${name}`;
    btn.textContent = `🔄 ${name}`;
    btn.className = "source-button";
    btn.onclick = async () => {
      btn.disabled = true;
      await fetch(`/sources/${encodeURIComponent(name)}/update`, { method: "POST" });
      // refresh here, if necessary
      btn.disabled = false;
    };
    sourcesDiv.appendChild(btn);
  });
}

function createSongElem(rawName) {
  const li = document.createElement("li");
  li.className = "song-entry";

  const img = document.createElement("img");
  img.src = `/album-art/${encodeURIComponent(rawName)}`;
  img.className = "album-art";
  img.alt = `Album art for ${rawName}`;
  img.onerror = () => {
    img.style.display = "none"; // Hide if image doesn't load
  };

  const span = document.createElement("span");
  span.className = "song-title";

  span.textContent = rawName;
  fetch(`/song_data/display_name/${encodeURIComponent(rawName)}`)
    .then(response => response.json())
    .then(displayName => {
      span.textContent = displayName;
    })
    .catch(err => {
      console.error("Failed to load display name:", err);
    });

  li.appendChild(img);
  li.appendChild(span);

  return li
}

function updateSongElems(songs) {
  songListElem.innerHTML = "";

  songs.forEach(rawName => {
    const li = createSongElem(rawName);
    li.onclick = () => selectSongAsRoot(rawName, true);
    songListElem.appendChild(li);
  });
}

function updatePlaylistSongElems() {
  playListElem.innerHTML = "";

  currentPlaylist.forEach(rawName => {
    const li = createSongElem(rawName);
    li.onclick = () => selectSongAsCurrentlyPlaying(rawName, true);
    playListElem.appendChild(li);
  });
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

playPauseBtn.onclick = () => {
  setPlaying(audio.paused);
};

audio.addEventListener("loadedmetadata", () => {
  totalDurationElem.textContent = formatTime(audio.duration);
  seekBar.max = seekbarResolutionHz*audio.duration;
});

audio.addEventListener("timeupdate", () => {
  seekBar.value = audio.currentTime*seekbarResolutionHz;
  currentTimeElem.textContent = formatTime(audio.currentTime);
});

audio.addEventListener("ended", () => {
    progressToNextSongInPlaylist();
});

seekBar.addEventListener("input", () => {
  audio.currentTime = seekBar.value/seekbarResolutionHz;
});

async function selectSongAsRoot(rawName, startPlaying) {
  const currentRootSong = rawName;
  
  selectSongAsCurrentlyPlaying(rawName, startPlaying);
  
  await createMusicGraph(rawName);
}

function progressToNextSongInPlaylist() {
  for (let i = 0; i < currentPlaylist.length - 2; i++){
    console.log(currentPlaylist[i], currentSongInPlayer);
    if (currentPlaylist[i] == currentSongInPlayer) {
      selectSongAsCurrentlyPlaying(currentPlaylist[i+1], true);
      return;
    }
  }
  selectSongAsRoot(currentPlaylist[currentPlaylist.length - 1], true);
}

async function selectSongAsCurrentlyPlaying(rawName, startPlaying) {
  const res = await fetch(`/songs/sampled_for/${encodeURIComponent(rawName)}?qt_songs=9`);
  const sortedSongs = await res.json();
  updateSongElems(sortedSongs);

  putSongInPlayer(rawName, startPlaying);
}

async function putSongInPlayer(rawName, startPlaying) {
  currentSongInPlayer = rawName;
  audio.src = `/audio/${encodeURIComponent(rawName)}`;
  response = await fetch(`/song_data/display_artist_and_name/${encodeURIComponent(rawName)}`);
  [artist, name] = await response.json();
  document.getElementById("track-title").textContent = name;
  document.getElementById("track-artist").textContent = artist;
  document.getElementById("footer-album-art").src = `/album-art/${encodeURIComponent(rawName)}`;
  setPlaying(startPlaying);
}

function setPlaying(playing) {
  if (playing) {
    audio.play();
    playPauseBtn.textContent = "⏸️";
  } else {
    audio.pause();
    playPauseBtn.textContent = "▶️";
  }
}

async function createMusicGraph(rawName) {
  const res = await fetch(`/playlists/playlist_from/${encodeURIComponent(rawName)}?with_playtree=true`);
  const [playlist, newSongs, children] = await res.json();
  currentPlaylist = playlist;
  updatePlaylistSongElems();
  currentTreeChildren = children;

  renderMusicGraph(playlist, newSongs, children);
}

async function createMusicGraphFromHead(playlist_head, startPlaying, modifyPlayer) {
  // modifyPlayer controls whether we should change which song is currently playing (in case it leaves the playlist)
  // if true, it inserts into the player the last song in the playlist head

  const querySubstring = playlist_head.map(raw_name => `head_raw_names=${encodeURIComponent(raw_name)}`).join(`&`);
  const queryString = `/playlists/playlist_from_head?` + querySubstring + `&with_playtree=true`;

  const res = await fetch(queryString);
  const [playlist, newSongs, children] = await res.json();
  currentPlaylist = playlist;
  updatePlaylistSongElems();
  currentTreeChildren = children;

  renderMusicGraph(playlist, newSongs, children);

  if (modifyPlayer) {
    selectSongAsCurrentlyPlaying(playlist_head[playlist_head.length-1], true);
  }
}

function getPlaylistHeadFrom(rawName) {
    var currentSongExpl = rawName;
    const tail = [];
    while (!(currentPlaylist.includes(currentSongExpl))){
        tail.push(currentSongExpl);
        // crappy dict inversion
        for (const potentialParent in currentTreeChildren) {
            if (currentTreeChildren[potentialParent].includes(currentSongExpl)){
                currentSongExpl = potentialParent;
                break;
            }
        }
    }
    return currentPlaylist.slice(0, currentPlaylist.indexOf(currentSongExpl) + 1).concat(tail.reverse());
}

function renderMusicGraph(playlist, extraSongs, children) {

    // graph setup

    const nodeRadius = 10;
    const margin = 50;
    const edge_length = 100;

    const graphBoundingBox = document.getElementById("musicGraph").getBoundingClientRect();
    const width = graphBoundingBox.width;
    const height = graphBoundingBox.height;

    const svg = d3.select("svg");

    // delete any previous graph
    svg.selectAll("*").remove();

    // Create a group for all graph elements
    const g = svg.append("g");

    // constructing graphData
    const idsByRawName = {};
    const nodes = [];
    const links = [];
    let i = 0;
    while (i < playlist.length) {
      idsByRawName[playlist[i]] = i;
      nodes.push({"id": i, "raw_name": playlist[i], "is_highlighted": true, x:width/2, y:height/2});
      i++;
    }
    for (let j = 0; j < extraSongs.length; j++) {
      idsByRawName[extraSongs[j]] = i+j;
      nodes.push({"id": i+j, "raw_name": extraSongs[j], "is_highlighted": false, x:width/2, y:height/2});
    }
    for (let i = 0; i < playlist.length-1; i++) {
      links.push({"source": i, "target": i + 1, "is_highlighted": true});
    }
    for (const [song, childSongs] of Object.entries(children)) {
        const songId = idsByRawName[song];
        for (const childSong of childSongs) {
            links.push({"source": songId, "target": idsByRawName[childSong], "is_highlighted": false});
        }
    }

    const pathNodeCount = playlist.length;
    const pathXPositions = Array.from({length: pathNodeCount}, (_, i) =>
      width * 0.1 + (width * 0.8) * (i / (pathNodeCount - 1))
    );

    const yOrd = height/2;
    var side_counter = 0;
    for (const raw_name of playlist) {
      const id = idsByRawName[raw_name];
      const node = nodes[id];
      const xOrd = pathXPositions[id];
      node.x = xOrd;
      node.y = yOrd;
      if (!(raw_name in children)) continue;
      for (const child_name of children[raw_name]){
        const child_id = idsByRawName[child_name];
        const child_node = nodes[child_id];
        const node_goes_up = Math.random() > (1+Math.max(side_counter, 0))/(2+Math.abs(side_counter));
        child_node.x = xOrd + edge_length;
        side_counter += node_goes_up ? 1 : -1;
        const yDispl = node_goes_up ? edge_length : -edge_length;
        child_node.y = yOrd + yDispl;
        if (!(child_name in children)) continue;
        for (const grandchild_name of children[child_name]){
          const grandchild_id = idsByRawName[grandchild_name];
          const grandchild_node = nodes[grandchild_id];
          grandchild_node.x = xOrd + 2 * edge_length;
          grandchild_node.y = yOrd + 2 * yDispl;
        }
      }
    }

    const graphData = {
      nodes: nodes,
      links: links,
      highlighted_path: playlist
    };



    // SIMULATION

    const simulation = d3.forceSimulation(graphData.nodes)
      .alphaMin(0.001)
      .alphaDecay(0.0005);

    simulation
      .force("charge", d3.forceManyBody().strength(-30).distanceMax(100)) // repulsion btw closeby nodes
      //.force("charge", d3.forceManyBody().strength(-1000).distanceMax(50)) // repulsion btw closeby nodes
      .force("collision", d3.forceCollide().radius(nodeRadius)) // avoid overlapping
      .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(edge_length).strength(1)) // adjacents can't be too far
      //.force("center", d3.forceCenter(width / 2, height / 2)) // pull twrd center, for debug

    //some extra nonstd forces
    simulation.force("bounds", (alpha) => {
      graphData.nodes.forEach(node => {
        // boundary repel force
        if (node.x < margin) node.vx += (margin - node.x) * 0.1 * alpha;
        if (node.x > width - margin) node.vx -= (node.x - (width - margin)) * 0.1 * alpha;
        if (node.y < margin) node.vy += (margin - node.y) * 0.1 * alpha;
        if (node.y > height - margin) node.vy -= (node.y - (height - margin)) * 0.1 * alpha;
        // mild rightward flow (with a kickstart)
        // if (alpha > 0.95) { node.vx += 100 * (alpha-0.95); }
        // else { node.vx += 0.5 * alpha ;}
        node.vx += 0.5 * alpha ;
      });
    });

    // update positions acc. to speed each tick of the sim
    simulation.on("tick", () => {
      node
        .attr("transform", d => `translate(${d.x},${d.y})`);
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
    });



    // HIGHLIGHTED PATH

    // technically also simulation - some extra scaffolding st highlighted path is laid out along the middle
    // Calculate positions for highlighted nodes

    // Create a map for quick lookup of highlighted nodes
    const highlightedNodes = new Set(graphData.highlighted_path);

    // Add strong positioning force for highlighted nodes
    simulation.force("highlighted", (alpha) => {
      graphData.nodes.forEach(node => {
        if (highlightedNodes.has(node.raw_name)) {
          // from some logs here learned that nodes are just straight up the same object i passed originally, same place
          // we could edit those .vx's directly
          const index = graphData.highlighted_path.indexOf(node.raw_name);
          const targetX = pathXPositions[index];
          const targetY = height / 2;

          // Strong attraction to fixed position
          node.vx += (targetX - node.x) * 0.2;
          node.vy += (targetY - node.y) * 0.2;
        } else {
          const offMiddle = node.y - height/2;
          const strength = Math.abs(offMiddle) < nodeRadius ? 2 : 0.2;
          node.vy += Math.sign(offMiddle) * strength * alpha;
        }
      });
    });



    // GRAPH OBJECTS

    // edges
    const link = g.append("g")
      .selectAll("line")
      .data(graphData.links)
      .enter().append("line")
        .attr("stroke", d => d.is_highlighted ? "#fff" : "#aaa")
        .attr("stroke-width", d => d.is_highlighted ? 2 : 1);

    // node click logic
    const node = g.append("g")
      .selectAll("g")
      .data(graphData.nodes)
      .enter().append("g")
        .on("click", (event, d) => {
          if (currentPlaylist.includes(d.raw_name)) {
            if (currentPlaylist[currentPlaylist.length - 1] == d.raw_name) {
              selectSongAsRoot(d.raw_name, true);
            } else {
              selectSongAsCurrentlyPlaying(d.raw_name, true);
            }
          } else {
            const playlistHead = getPlaylistHeadFrom(d.raw_name);
            const currentSongIsInHead = playlistHead.includes(currentSongInPlayer);
            createMusicGraphFromHead(playlistHead, true, !currentSongIsInHead)
          }
        });

    // node circles (fallback)
    node.append("circle")
      .attr("r", nodeRadius*1.1)
      .attr("fill", d => graphData.highlighted_path.includes(d.raw_name) ? "#fff" : "#aaa");

    // node images (stolen code)
    node.each(function(d) {
      const nodeGroup = d3.select(this);

      // clip path
      nodeGroup.append("clipPath")
        .attr("id", `clip-${d.id}`)
        .append("circle")
          .attr("r", nodeRadius);

      // add image w/ clip path
      nodeGroup.append("image")
        .attr("xlink:href", `/album-art/${d.raw_name}`)
        .attr("x", -nodeRadius)
        .attr("y", -nodeRadius)
        .attr("width", 2*nodeRadius)
        .attr("height", 2*nodeRadius)
        .attr("clip-path", `url(#clip-${d.id})`);
    });
}

window.addEventListener("DOMContentLoaded", () => {
  fetchSources();
  fetch("/songs/random")
    .then(response => {
      if (!response.ok) throw new Error("Failed to fetch random song");
      return response.text();
    })
    .then(quotedRawName => {
      const rawName = quotedRawName.slice(1, quotedRawName.length-1)
      selectSongAsRoot(rawName, false);
    })
});




