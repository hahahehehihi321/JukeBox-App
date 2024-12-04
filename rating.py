import customtkinter as ctk

class ModernRatingDialog:
    def __init__(self, parent, library, track_key, callback):
        """
        Initialize Modern Rating Dialog
        
        Args:
            parent: Parent window (CTk root or CTkToplevel)
            library: JsonLibrary instance
            track_key: Key of the track being rated
            callback: Function to call after successful rating update
        """
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Update Rating")
        self.dialog.geometry("300x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Store references
        self.library = library
        self.track_key = track_key
        self.callback = callback
        
        # Center the dialog
        x = parent.winfo_x() + (parent.winfo_width() - 300) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self._create_widgets()
        self._setup_bindings()
        
    def _create_widgets(self):
        """Create and setup all dialog widgets"""
        # Title label
        track_name = self.library.get_name(self.track_key)
        current_rating = self.library.get_rating(self.track_key)
        
        title_text = f"Rate: {track_name}\nCurrent Rating: {current_rating}"
        self.title_label = ctk.CTkLabel(
            self.dialog,
            text=title_text,
            font=("Helvetica", 14)
        )
        self.title_label.pack(pady=15)
        
        # Star rating frame
        self.star_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self.star_frame.pack(pady=15)
        
        self.star_labels = []
        for i in range(5):
            label = ctk.CTkLabel(
                self.star_frame,
                text="★",
                font=("Helvetica", 24),
                text_color="gray",
                cursor="hand2"
            )
            label.pack(side="left", padx=4)
            label.bind("<Button-1>", lambda e, rating=i+1: self.set_rating(rating))
            self.star_labels.append(label)
        
        # Rating entry frame
        self.entry_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self.entry_frame.pack(pady=15)
        
        self.entry_label = ctk.CTkLabel(
            self.entry_frame,
            text="Or enter rating (1-5):",
            font=("Helvetica", 12)
        )
        self.entry_label.pack(side="left", padx=5)
        
        self.rating_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(
            self.entry_frame,
            textvariable=self.rating_var,
            width=60,
            justify="center"
        )
        self.entry.pack(side="left", padx=5)
        
        # Button frame
        self.button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        self.button_frame.pack(pady=20)
        
        self.update_button = ctk.CTkButton(
            self.button_frame,
            text="Update",
            command=self.validate_and_update,
            width=100
        )
        self.update_button.pack(side="left", padx=5)
        
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            width=100
        )
        self.cancel_button.pack(side="left", padx=5)
        
        # Update initial star display
        if current_rating > 0:
            self.update_star_display(current_rating)
            self.rating_var.set(str(current_rating))
    
    def update_star_display(self, rating):
        """Update the visual star display"""
        for i, label in enumerate(self.star_labels):
            if i < rating:
                label.configure(text_color="gold")
            else:
                label.configure(text_color="gray")
    
    def set_rating(self, rating):
        """Set rating from star click"""
        self.rating_var.set(str(rating))
        self.update_star_display(rating)
    
    def _setup_bindings(self):
        """Setup keyboard bindings"""
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.validate_and_update())
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())
        self.rating_var.trace_add("write", lambda *args: self.handle_rating_input())
    
    def handle_rating_input(self):
        """Handle rating input changes"""
        try:
            rating = int(self.rating_var.get())
            if 1 <= rating <= 5:
                self.update_star_display(rating)
        except ValueError:
            pass
    
    def validate_and_update(self):
        """Validate input and update rating"""
        try:
            new_rating = int(self.rating_var.get())
            if 1 <= new_rating <= 5:
                if self.library.update_rating(self.track_key, new_rating):
                    self.callback()  # Refresh display
                    self.dialog.destroy()
                else:
                    self.show_error("Error", "Failed to update rating")
            else:
                self.show_error("Error", "Rating must be between 1 and 5")
        except ValueError:
            self.show_error("Error", "Please enter a valid number")
    
    def show_error(self, title, message):
        """Display an error message"""
        error_dialog = ctk.CTkToplevel(self.dialog)
        error_dialog.title(title)
        error_dialog.geometry("300x150")
        
        # Center the error dialog
        x = self.dialog.winfo_x() + (self.dialog.winfo_width() - 300) // 2
        y = self.dialog.winfo_y() + (self.dialog.winfo_height() - 150) // 2
        error_dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            error_dialog,
            text=message,
            font=("Helvetica", 12)
        ).pack(pady=20)
        
        ctk.CTkButton(
            error_dialog,
            text="OK",
            command=error_dialog.destroy,
            width=80
        ).pack(pady=10)