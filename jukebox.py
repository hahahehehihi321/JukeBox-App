import customtkinter as ctk
from tkinter import messagebox, filedialog
import pygame
import os
from mutagen.mp3 import MP3
import time
from threading import Thread
from youtube_search import YoutubeSearch
import string
import yt_dlp
from library_new import JsonLibrary
from PIL import Image
from rating import ModernRatingDialog

# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_song = None
        self.is_playing = False
        self.is_paused = False
        self.paused_position = 0
        self.current_position = 0

    def load_audio(self, song_path):
        pygame.mixer.music.load(song_path)
        self.current_song = song_path
        self.paused_position = 0

    def start_playback(self, start_pos=0):
        if self.is_paused:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.play(start=start_pos)
        self.is_playing = True
        self.is_paused = False

    def suspend_playback(self):
        pygame.mixer.music.pause()
        self.is_playing = False
        self.is_paused = True

    def terminate_playback(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0

    def adjust_volume(self, volume):
        pygame.mixer.music.set_volume(volume)

class AudioTrack:
    def __init__(self, path, title=None, source="local"):
        self.path = path
        self.source = source
        self.title = title or os.path.basename(path)
        self.duration = self._calculate_duration()

    def _calculate_duration(self):
        try:
            audio = MP3(self.path)
            return audio.info.length
        except:
            return 0

class YoutubeAudioDownloader:
    def __init__(self, download_path="downloads"):
        self.download_path = download_path
        if not os.path.exists(download_path):
            os.makedirs(download_path)
    
    def sanitize_filename(self, title):
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c for c in title if c in valid_chars)
        return filename[:50]
    
    def fetch_audio(self, url, progress_callback=None):
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_callback] if progress_callback else None,
                'default_search': 'ytsearch',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if 'entries' in info:
                    info = info['entries'][0]
                filename = ydl.prepare_filename(info)
                mp3_path = os.path.splitext(filename)[0] + '.mp3'
                return mp3_path
                
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

class ModernJukeboxInterface:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Modern Jukebox")
        self.window.geometry("1200x800")
        
        self.music_library = JsonLibrary()
        self.audio_player = AudioPlayer()
        self.downloader = YoutubeAudioDownloader()
        self.playlist = []
        self.current_track_index = -1
        self.is_seeking = False
        self.playback_start_time = 0
        self.seek_position = 0

        self.selected_track_index = -1

        self._initialize_interface()
        self._initialize_progress_updater()
    def _initialize_interface(self):
        # Main container initialization
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Top section with search and track ID
        self.top_frame = ctk.CTkFrame(self.main_frame)
        self.top_frame.pack(fill="x", padx=10, pady=10)

        # Search section setup
        self.search_frame = ctk.CTkFrame(self.main_frame)
        self.search_frame.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(
            self.search_frame, 
            placeholder_text="Search YouTube or enter URL",
            width=400
        )
        self.search_entry.pack(side="left", padx=10)

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search",
            command=self.search_youtube_content,
            width=100
        )
        self.search_button.pack(side="left", padx=5)

        self.download_button = ctk.CTkButton(
            self.search_frame,
            text="Download",
            command=self.initiate_youtube_download,
            width=100
        )
        self.download_button.pack(side="left", padx=5)

        # Track ID controls setup
        self.track_frame = ctk.CTkFrame(self.top_frame)
        self.track_frame.pack(side="right", padx=10)

        self.track_id_label = ctk.CTkLabel(
            self.track_frame,
            text="Track ID:"
        )
        self.track_id_label.pack(side="left", padx=5)

        self.track_id_entry = ctk.CTkEntry(
            self.track_frame,
            width=80,
            placeholder_text="ID"
        )
        self.track_id_entry.pack(side="left", padx=5)

        self.local_lib_button = ctk.CTkButton(
            self.track_frame,
            text="View Local Track",
            command=self.retrieve_library_track,
            width=120
        )
        self.local_lib_button.pack(side="left", padx=5)

        # Search results area
        self.results_frame = ctk.CTkFrame(self.main_frame)
        self.results_frame.pack(fill="x", padx=10, pady=10)

        self.search_results = ctk.CTkTextbox(
            self.results_frame,
            height=100
        )
        self.search_results.pack(fill="x", padx=10, pady=5)
        self.search_results.bind('<Double-Button-1>', self.download_selected_track)

        # Content area with playlist and library
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Playlist section setup
        self.playlist_frame = ctk.CTkFrame(self.content_frame)
        self.playlist_frame.pack(side="left", fill="both", expand=True, padx=5)

        self.playlist_label = ctk.CTkLabel(
            self.playlist_frame,
            text="Playlist",
            font=("Helvetica", 16, "bold")
        )
        self.playlist_label.pack(padx=5)

        self.playlist_box = ctk.CTkTextbox(
            self.playlist_frame,
            height=300
        )
        self.playlist_box.pack(fill="both", expand=True, padx=10, pady=5)
        self.playlist_box.bind('<Button-1>', self.handle_playlist_selection)

        # Library section setup
        self.library_frame = ctk.CTkFrame(self.content_frame)
        self.library_frame.pack(side="right", fill="both", expand=True, padx=5)

        self.library_label = ctk.CTkLabel(
            self.library_frame,
            text="Library",
            font=("Helvetica", 16, "bold")
        )
        self.library_label.pack(pady=5)

        self.library_box = ctk.CTkTextbox(
            self.library_frame,
            height=300
        )
        self.library_box.pack(fill="both", expand=True, padx=10, pady=5)

        # Playback controls setup
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.pack(fill="x", padx=10, pady=10, expand=True)

        # Now playing display
        self.now_playing_label = ctk.CTkLabel(
            self.controls_frame,
            text="No song playing",
            font=("Helvetica", 14)
        )
        self.now_playing_label.pack(pady=5)

        # Progress tracking
        self.progress_bar = ctk.CTkProgressBar(
            self.controls_frame,
            width=400
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        # Time tracking display
        self.time_label = ctk.CTkLabel(
            self.controls_frame,
            text="0:00 / 0:00"
        )
        self.time_label.pack(pady=5)

        # Control buttons container
        self.buttons_frame = ctk.CTkFrame(self.controls_frame)
        self.buttons_frame.pack(pady=10)

        # Playback controls layout
        self.playback_controls_frame = ctk.CTkFrame(self.buttons_frame, fg_color="transparent")
        self.playback_controls_frame.pack(side="left", padx=10)

        # Playlist management buttons
        self.clear_playlist_button = ctk.CTkButton(
            self.playback_controls_frame,
            text="Clear Playlist",
            command=self.clear_playlist_contents,
            width=100
        )
        self.clear_playlist_button.pack(side="left", padx=5)

        self.update_rating_button = ctk.CTkButton(
            self.playback_controls_frame,
            text="Update Rating",
            command=self.display_rating_dialog,
            width=100
        )
        self.update_rating_button.pack(side="left", padx=5)

        self.add_local_button = ctk.CTkButton(
            self.playback_controls_frame,
            text="Add Local Files",
            command=self.import_local_tracks,
            width=100
        )
        self.add_local_button.pack(side="left", padx=5)

        # Playback control buttons
        self.prev_button = ctk.CTkButton(
            self.playback_controls_frame,
            text="⏮",
            width=60,
            command=self.play_previous_track
        )
        self.prev_button.pack(side="left", padx=5)

        self.play_button = ctk.CTkButton(
            self.playback_controls_frame,
            text="▶",
            width=60,
            command=self.toggle_playback
        )
        self.play_button.pack(side="left", padx=5)

        self.next_button = ctk.CTkButton(
            self.playback_controls_frame,
            text="⏭",
            width=60,
            command=self.play_next_track
        )
        self.next_button.pack(side="left", padx=5)

        # Volume control setup
        self.volume_control_frame = ctk.CTkFrame(self.buttons_frame, fg_color="transparent")
        self.volume_control_frame.pack(side="left", padx=10, fill="x", expand=True)

        self.volume_icon_label = ctk.CTkLabel(
            self.volume_control_frame,
            text="🔊",
            font=("Helvetica", 14)
        )
        self.volume_icon_label.pack(side="left", padx=5)

        self.volume_slider = ctk.CTkSlider(
            self.volume_control_frame,
            from_=0,
            to=1,
            command=self.adjust_volume_level,
            width=150
        )
        self.volume_slider.pack(side="left", padx=5, fill="x", expand=True)
        self.volume_slider.set(0.5)  # Default volume 50%

    def _initialize_progress_updater(self):
        def update_progress():
            while True:
                if self.audio_player.is_playing and not self.audio_player.is_paused:
                    try:
                        elapsed_time = time.time() - self.playback_start_time
                        current_track = self.playlist[self.current_track_index]
                        
                        # Calculate and bound progress between 0 and 1
                        progress = (elapsed_time / current_track.duration) if current_track.duration > 0 else 0
                        progress = min(1.0, max(0, progress))

                        # Update UI elements in the main thread
                        self.window.after(0, lambda: (
                            self.progress_bar.set(progress),
                            self.time_label.configure(text=f"{time.strftime('%M:%S', time.gmtime(elapsed_time))} / {time.strftime('%M:%S', time.gmtime(current_track.duration))}")
                        ))

                        # Check if track has finished playing
                        if elapsed_time >= current_track.duration:
                            self.window.after(0, self.play_next_track)

                    except Exception as e:
                        print(f"Progress update error: {e}")

                time.sleep(0.1)

        self.update_thread = Thread(target=update_progress, daemon=True)
        self.update_thread.start()

    def initiate_seek(self, event):
        """Initialize seeking operation when progress bar is clicked"""
        if self.current_track_index >= 0:
            self.is_seeking = True
            self.update_seek_position(event)

    def update_seek_position(self, event):
        """Update seek position while dragging"""
        if self.current_track_index >= 0 and self.is_seeking:
            progress_width = self.progress_bar.winfo_width()
            relative_x = max(0, min(event.x, progress_width))
            seek_ratio = relative_x / progress_width
            
            current_track = self.playlist[self.current_track_index]
            new_position = seek_ratio * current_track.duration
            
            # Update visual feedback
            self.progress_bar.set(seek_ratio)
            
            # Update time display
            current_str = time.strftime('%M:%S', time.gmtime(new_position))
            duration_str = time.strftime('%M:%S', time.gmtime(current_track.duration))
            self.time_label.configure(text=f"{current_str} / {duration_str}")

            self.seek_position = new_position

    def finalize_seek(self, event):
        """Complete the seeking operation"""
        if self.current_track_index >= 0 and self.is_seeking:
            self.is_seeking = False
            was_playing = self.audio_player.is_playing and not self.audio_player.is_paused
            
            # Apply the seek operation
            pygame.mixer.music.play(start=self.seek_position)
            
            # Restore previous playback state
            if not was_playing:
                pygame.mixer.music.pause()
            
            # Update timing reference
            self.playback_start_time = time.time() - self.seek_position

    def adjust_playback_position(self, seconds):
        """Adjust playback position by relative number of seconds"""
        if self.current_track_index >= 0:
            current_time = time.time() - self.playback_start_time
            current_track = self.playlist[self.current_track_index]
            
            # Calculate and bound new position
            new_position = max(0, min(current_track.duration, current_time + seconds))
            
            # Store playback state
            was_playing = self.audio_player.is_playing and not self.audio_player.is_paused
            
            # Apply new position
            pygame.mixer.music.play(start=new_position)
            
            if not was_playing:
                pygame.mixer.music.pause()
            
            # Update timing reference and progress display
            self.playback_start_time = time.time() - new_position
            self.seek_position = new_position
            
            if current_track.duration > 0:
                self.progress_bar.set(new_position / current_track.duration)
            
            # Update time display
            current_str = time.strftime('%M:%S', time.gmtime(new_position))
            duration_str = time.strftime('%M:%S', time.gmtime(current_track.duration))
            self.time_label.configure(text=f"{current_str} / {duration_str}")

    def toggle_playback(self):
        """Toggle between play and pause states"""
        if self.current_track_index < 0 and self.playlist:
            # Start playing first track if none is playing
            self.current_track_index = 0
            self.start_playback()
        elif self.audio_player.is_playing:
            # Pause current track
            self.audio_player.current_position = time.time() - self.playback_start_time
            self.audio_player.suspend_playback()
            self.play_button.configure(text="▶")
        else:
            # Resume playback
            if self.audio_player.is_paused:
                self.playback_start_time = time.time() - self.audio_player.current_position
                self.audio_player.start_playback()
                self.play_button.configure(text="⏸")
            else:
                self.start_playback()

    def play_next_track(self):
        """Play the next track in the playlist"""
        if self.current_track_index < len(self.playlist) - 1:
            self.current_track_index += 1
            self.start_playback()
            
            # Update display
            self.refresh_playlist_display()
            current_pos = float(self.current_track_index) + 1
            self.playlist_box.see(f"{current_pos}")
        else:
            # End of playlist reached
            self.audio_player.terminate_playback()
            self.play_button.configure(text="▶")
            self.now_playing_label.configure(text="No song playing")
            self.progress_bar.set(0)
            self.time_label.configure(text="0:00 / 0:00")

    def play_previous_track(self):
        """Play the previous track in the playlist"""
        if self.current_track_index > 0:
            self.current_track_index -= 1
            self.start_playback()
            
            # Update display
            self.refresh_playlist_display()
            current_pos = float(self.current_track_index) + 1
            self.playlist_box.see(f"{current_pos}")
        else:
            # At start of playlist, restart current track
            self.start_playback()

    def search_youtube_content(self):
        """Search YouTube for content based on user query"""
        query = self.search_entry.get().strip()
        if not query:
            return
                
        try:
            # Clear previous results
            self.search_results.delete("1.0", "end")
            
            # Show searching indicator
            self.search_results.insert("1.0", "Searching...")
            self.search_results.update()
            
            # Execute search
            results = YoutubeSearch(query, max_results=5).to_dict()
            
            # Clear searching indicator
            self.search_results.delete("1.0", "end")
            
            # Display formatted results
            for i, result in enumerate(results, 1):
                title = result['title']
                duration = result.get('duration', 'Unknown duration')
                channel = result.get('channel', 'Unknown channel')
                url = f"https://youtube.com/watch?v={result['id']}"
                
                result_text = (f"{i}. {title}\n"
                            f"   Duration: {duration} | Channel: {channel}\n"
                            f"   URL: {url}\n\n")
                
                self.search_results.insert("end", result_text)
            
            # Add usage instructions
            self.search_results.insert("end", "-" * 50 + "\n")
            self.search_results.insert("end", "Double-click a result to download\n")
            
        except Exception as e:
            self.display_error_message("Search Error", str(e))
            # Auto-clear error after delay
            self.window.after(3000, lambda: self.search_results.delete("1.0", "end"))

    def download_selected_track(self, event):
        """Handle download of selected search result"""
        try:
            # Identify clicked line
            click_pos = self.search_results.index("@%d,%d" % (event.x, event.y))
            line_start = f"{int(float(click_pos))}.0"
            line_end = f"{int(float(click_pos))}.end"
            clicked_line = self.search_results.get(line_start, line_end)
            
            # Extract URL if present
            if "URL: " in clicked_line:
                url = clicked_line.split("URL: ")[1].strip()
                self.search_entry.delete(0, "end")
                self.search_entry.insert(0, url)
                self.initiate_youtube_download()
                
        except Exception as e:
            print(f"Download selection error: {e}")

    def initiate_youtube_download(self):
        """Download audio from YouTube URL or search query"""
        query = self.search_entry.get().strip()
        if not query:
            return

        # Convert search terms to YouTube search if not URL
        if not query.startswith(('http://', 'https://')):
            query = f"ytsearch1:{query}"

        try:
            # Create download progress window
            progress_window = ctk.CTkToplevel(self.window)
            progress_window.title("Downloading...")
            progress_window.geometry("400x200")
        
            # Center progress window
            x = self.window.winfo_x() + (self.window.winfo_width() - 400) // 2
            y = self.window.winfo_y() + (self.window.winfo_height() - 200) // 2
            progress_window.geometry(f"+{x}+{y}")
        
            # Progress indicators
            progress_label = ctk.CTkLabel(
                progress_window,
                text="Downloading audio...",
                font=("Helvetica", 14)
            )
            progress_label.pack(pady=20)
            
            progress_bar = ctk.CTkProgressBar(progress_window)
            progress_bar.pack(pady=20, padx=40, fill="x")
            progress_bar.set(0)
            
            status_label = ctk.CTkLabel(
                progress_window,
                text="Starting download...",
                font=("Helvetica", 12)
            )
            status_label.pack(pady=10)

            def update_progress(d):
                """Handle download progress updates"""
                if d['status'] == 'downloading':
                    try:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        downloaded = d.get('downloaded_bytes', 0)
                        
                        if total > 0:
                            # Update progress visualization
                            progress = downloaded / total
                            self.window.after(0, lambda: progress_bar.set(progress))
                            
                            # Update status with speed and ETA
                            speed = d.get('speed', 0)
                            if speed:
                                speed_mb = speed / (1024 * 1024)
                                eta = d.get('eta', 0)
                                status_text = f"Speed: {speed_mb:.1f} MB/s | ETA: {eta} seconds"
                                self.window.after(0, lambda: status_label.configure(text=status_text))
                                
                    except Exception as e:
                        print(f"Progress update error: {e}")
            
                elif d['status'] == 'finished':
                    self.window.after(0, lambda: status_label.configure(text="Processing audio..."))
        
            def download_thread():
                """Execute download in separate thread"""
                try:
                    # Download audio file
                    output_path = self.downloader.fetch_audio(
                        query,
                        progress_callback=update_progress
                    )
                    
                    # Create track object and add to playlist
                    track = AudioTrack(output_path, source="youtube")
                    self.playlist.append(track)
                    
                    # Update UI
                    self.window.after(0, self.refresh_playlist_display)
                    self.window.after(0, progress_window.destroy)
                    self.window.after(0, lambda: self.display_info_message(
                        "Success",
                        "Track downloaded and added to playlist!"
                    ))
                    
                except Exception as e:
                    self.window.after(0, progress_window.destroy)
                    self.window.after(0, lambda: self.display_error_message(
                        "Download Error",
                        str(e)
                    ))
            
            # Launch download thread
            Thread(target=download_thread, daemon=True).start()
        
        except Exception as e:
            self.display_error_message("Download Error", str(e))

    def retrieve_library_track(self):
        """Retrieve and display track information from library"""
        track_id = self.track_id_entry.get()

        if not track_id:
            self.display_error_message("Error", "Please enter a track ID")
            return
            
        track_name = self.music_library.get_name(track_id)
        if track_name is not None:
            artist = self.music_library.get_artist(track_id)
            rating = self.music_library.get_rating(track_id)
            play_count = self.music_library.get_play_count(track_id)
            
            # Format track details for display
            track_details = (
                f"Track ID: {track_id}\n"
                f"Title: {track_name}\n"
                f"Artist: {artist}\n"
                f"Rating: {'★' * rating}{'☆' * (5-rating)}\n"
                f"Play Count: {play_count}\n"
                f"{'-'*30}"
            )
            
            # Update library display
            self.library_box.delete("1.0", "end")
            self.library_box.insert("1.0", track_details)
            
            # Store current track reference
            self.current_library_track = track_id
        else:
            self.library_box.delete("1.0", "end")
            self.library_box.insert("1.0", f"Track {track_id} not found")
            self.current_library_track = None

    def initiate_library_playback(self, event=None):
        """Start playback of a track from the library"""
        if not hasattr(self, 'current_library_track') or self.current_library_track is None:
            return
            
        track_id = self.current_library_track
        file_path = self.music_library.get_file_path(track_id)
        
        if file_path and os.path.exists(file_path):
            # Create track object
            track = AudioTrack(
                file_path,
                title=self.music_library.get_name(track_id),
                source="library"
            )
            
            # Add to playlist if not present
            if track.path not in [t.path for t in self.playlist]:
                self.playlist.append(track)
                self.refresh_playlist_display()
            
            # Find track index in playlist
            for i, t in enumerate(self.playlist):
                if t.path == track.path:
                    self.current_track_index = i
                    break
            
            # Start playback
            self.start_playback()
            
            # Update play count
            self.music_library.increment_play_count(track_id)
        else:
            self.display_error_message("Error", "Track file not found. Please verify the file path in the library.")

    def import_local_tracks(self):
        """Import local MP3 files into the library and playlist"""
        file_paths = filedialog.askopenfilenames(
            title="Select MP3 Files",
            filetypes=[("MP3 Files", "*.mp3")]
        )
        
        for path in file_paths:
            # Create track object
            track = AudioTrack(path, source="local")
            
            # Check for existing track in library
            track_exists = False
            for key in self.music_library.library.keys():
                if self.music_library.get_file_path(key) == path:
                    track_exists = True
                    break
            
            # Add to library if new
            if not track_exists:
                next_id = str(len(self.music_library.library) + 1).zfill(2)
                self.music_library.library[next_id] = {
                    'name': os.path.basename(path),
                    'artist': 'Unknown',
                    'file_path': path,
                    'rating': 0,
                    'play_count': 0
                }
                self.music_library._save_library()
            
            # Add to playlist if not present
            if track.path not in [t.path for t in self.playlist]:
                self.playlist.append(track)
        
        # Update display
        self.refresh_playlist_display()

    def display_rating_dialog(self):
        """Display dialog for updating track rating"""
        track_id = self.track_id_entry.get().strip()

        if track_id:
            if self.music_library.get_name(track_id) is not None:
                ModernRatingDialog(
                    parent=self.window,
                    library=self.music_library,
                    track_key=track_id,
                    callback=self.update_library_display
                )
            else:
                self.display_info_message("Info", "Track ID not found in library.")
        else:
            self.display_info_message("Info", "Please enter a Track ID.")

    def update_library_display(self):
        """Refresh the library display after updates"""
        if hasattr(self, 'current_library_track'):
            self.retrieve_library_track()

    def process_result_click(self, event):
        """Handle clicks in the library results"""
        if not hasattr(self, 'current_library_track') or self.current_library_track is None:
            return
        
        try:
            click_pos = self.library_box.index("@%d,%d" % (event.x, event.y))
            line_num = int(float(click_pos))
            
            if not hasattr(self, 'rating_button'):
                self.rating_button = ctk.CTkButton(
                    self.library_frame,
                    text="Update Rating",
                    command=self.display_rating_dialog
                )
                self.rating_button.pack(pady=10)
            
            self.rating_button.pack()
        except ValueError:
            pass

    def start_playback(self):
        """Start playback of the current track"""
        if not self.playlist:
            return
                
        try:
            selection = self.playlist_box.get("sel.first", "sel.last")
        except Exception:
            selection = None
                
        if selection:
            selected_title = selection.strip()
            for i, track in enumerate(self.playlist):
                if track.title in selected_title:
                    self.current_track_index = i
                    break
        elif self.current_track_index < 0:
            self.current_track_index = 0
                    
        track = self.playlist[self.current_track_index]

        # Check library association
        track_path = track.path
        track_id = None
        
        for key in self.music_library.library.keys():
            if self.music_library.get_file_path(key) == track_path:
                track_id = key
                break
        
        if track_id:
            self.music_library.increment_play_count(track_id)
            
        # Initialize playback
        self.audio_player.load_audio(track.path)
        self.playback_start_time = time.time()
        self.audio_player.current_position = 0
        self.audio_player.start_playback()
            
        # Update interface
        self.now_playing_label.configure(text=f"Now playing: {track.title}")
        self.play_button.configure(text="⏸")
        self.refresh_playlist_display()

    def handle_playlist_selection(self, event):
        """Handle selection of tracks in the playlist"""
        try:
            # Get selected line
            index = self.playlist_box.index(f"@{event.x},{event.y}")
            line_start = f"{int(float(index))}.0"
            line_end = f"{int(float(index))}.end"
            clicked_line = self.playlist_box.get(line_start, line_end)
            
            # Find corresponding track
            for i, track in enumerate(self.playlist):
                prefix = "▶ " if i == self.current_track_index else "  "
                duration = time.strftime('%M:%S', time.gmtime(track.duration))
                display_line = f"{prefix}{track.title} ({duration})"
                if display_line.strip() == clicked_line.strip():
                    self.selected_track_index = i
                    break
        except Exception as e:
            print(f"Playlist selection error: {e}")
            self.selected_track_index = -1

    def clear_playlist_contents(self):
        """Clear the entire playlist and stop playback"""
        if self.audio_player.is_playing:
            self.audio_player.suspend_playback()
        
        # Reset playlist data
        self.playlist = []
        self.current_track_index = -1
        
        # Reset interface elements
        self.playlist_box.delete("1.0", "end")
        self.now_playing_label.configure(text="No song playing")
        self.play_button.configure(text="▶")
        self.time_label.configure(text="0:00 / 0:00")
        self.progress_bar.set(0)

    def refresh_playlist_display(self):
        """Update the playlist display"""
        self.playlist_box.delete("1.0", "end")
        for i, track in enumerate(self.playlist):
            prefix = "▶ " if i == self.current_track_index else "  "
            duration = time.strftime('%M:%S', time.gmtime(track.duration))
            display_line = f"{prefix}{track.title} ({duration})\n"
            self.playlist_box.insert("end", display_line)

    def suspend_playback(self):
        """Pause or resume playback"""
        if self.audio_player.is_playing:
            self.audio_player.suspend_playback()
            self.play_button.configure(text="▶")
        else:
            # Resume from stored position
            self.playback_start_time = time.time() - self.audio_player.current_position
            self.audio_player.start_playback()
            self.play_button.configure(text="⏸")

    def adjust_volume_level(self, value):
        """Adjust the playback volume"""
        try:
            volume = float(value)
            self.audio_player.adjust_volume(volume)
            
            # Update volume icon
            if hasattr(self, 'volume_icon_label'):
                if volume == 0:
                    icon_text = "🔇"
                elif volume < 0.33:
                    icon_text = "🔈"
                elif volume < 0.66:
                    icon_text = "🔉"
                else:
                    icon_text = "🔊"
                self.volume_icon_label.configure(text=icon_text)
        except ValueError:
            print(f"Invalid volume value: {value}")

    def display_error_message(self, title, message):
        """Display error message dialog"""
        messagebox.showerror(title, message)

    def display_info_message(self, title, message):
        """Display information message dialog"""
        messagebox.showinfo(title, message)

    def launch_application(self):
        """Start the application main loop"""
        self.window.mainloop()

def main():
    """Main entry point for the Modern Jukebox application"""
    app = ModernJukeboxInterface()
    app.launch_application()

if __name__ == "__main__":
    main()