import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule, NgModel } from '@angular/forms';
import { ChatService } from '../chat-service';

@Component({
  imports: [CommonModule, FormsModule],
  selector: 'app-chat',
  styleUrl: './chat.css',
  templateUrl: './chat.html',
})
export class Chat {
  question = '';
  messages: any;
  constructor(private chatService: ChatService) {
    this.messages = this.chatService.messages;
  }
  envoyer() {
    // Supprime les espaces et arrete l'éxecution si la question est vide
    if (!this.question.trim()) {
      return;
    }
    this.chatService.assistance(this.question);
    this.question = '';
  }


}