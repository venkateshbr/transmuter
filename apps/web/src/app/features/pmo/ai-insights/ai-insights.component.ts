import { Component, inject, signal, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';

interface Message {
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
  sources?: { label: string; source_type: string; record_id?: string; url?: string }[];
  tool_trace?: { tool_name: string; status: string; summary: string; source_type: string }[];
  confidence?: number;
  proposed_actions?: ProposedAction[];
}

interface ProposedAction {
  id: string;
  action_type: string;
  title: string;
  description: string;
  payload: Record<string, unknown>;
  status: string;
}

@Component({
  selector: 'app-ai-insights',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-8 h-full flex flex-col space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end shrink-0">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            AI Portfolio Assistant<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Intelligent insights, scenario analysis, and compliance audit powered by PydanticAI.</p>
        </div>
        <div class="flex gap-2">
          <button (click)="clearChat()" class="btn-ghost text-sm">Clear Context</button>
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm flex items-center gap-2">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--t-accent)] opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-[var(--t-accent)]"></span>
            </span>
            <span class="text-[10px] font-bold uppercase tracking-wider">Agent Online</span>
          </div>
        </div>
      </div>

      <!-- Chat Container -->
      <div class="flex-1 flex flex-col min-h-0 bg-[var(--t-surface)] rounded-2xl border border-[var(--t-border)] shadow-xl overflow-hidden relative">
        
        <!-- Messages Area -->
        <div #scrollContainer class="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
          @if (messages().length === 0) {
            <div class="h-full flex flex-col items-center justify-center opacity-40 text-center px-12">
              <div class="w-16 h-16 bg-[var(--t-accent-soft)] rounded-full flex items-center justify-center mb-4">
                <svg class="w-8 h-8 text-[var(--t-accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 class="text-lg font-bold text-[var(--t-text-primary)]">How can I assist your portfolio today?</h3>
              <p class="text-sm text-[var(--t-text-secondary)] mt-2 max-w-sm">
                Try asking: "Which initiatives are at risk of missing their next gate?" or "Summarize the current portfolio health."
              </p>
            </div>
          }

          @for (msg of messages(); track msg.timestamp) {
            <div class="flex" [class.justify-end]="msg.role === 'user'">
              <div class="max-w-[80%] flex gap-4" [class.flex-row-reverse]="msg.role === 'user'">
                <!-- Avatar -->
                <div class="w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center font-bold text-[10px]"
                     [class.bg-[var(--t-accent)]]="msg.role === 'ai'"
                     [class.text-white]="msg.role === 'ai'"
                     [class.bg-[var(--t-surface-raised)]]="msg.role === 'user'"
                     [class.text-[var(--t-text-primary)]]="msg.role === 'user'">
                  {{ msg.role === 'ai' ? 'AI' : 'ME' }}
                </div>
                <!-- Content -->
                <div class="space-y-1">
                  <div class="p-4 rounded-2xl text-sm leading-relaxed"
                       [class.bg-[var(--t-accent-soft)]]="msg.role === 'ai'"
                       [class.text-[var(--t-text-primary)]]="msg.role === 'ai'"
                       [class.rounded-tl-none]="msg.role === 'ai'"
                       [class.bg-[var(--t-surface-raised)]]="msg.role === 'user'"
                       [class.text-[var(--t-text-primary)]]="msg.role === 'user'"
                       [class.rounded-tr-none]="msg.role === 'user'"
                       [innerHTML]="msg.content">
                  </div>
                  @if (msg.role === 'ai' && msg.sources?.length) {
                    <div class="flex flex-wrap gap-1 px-1">
                      @for (source of msg.sources; track source.label) {
                        <span class="border border-[var(--t-border)] bg-[var(--t-surface)] px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[var(--t-text-secondary)]">
                          {{ source.label }}
                        </span>
                      }
                    </div>
                  }
                  @if (msg.role === 'ai' && msg.tool_trace?.length) {
                    <div class="space-y-1 border-l-2 border-[var(--t-border)] pl-3">
                      @for (trace of msg.tool_trace; track trace.tool_name) {
                        <p class="text-[10px] font-bold uppercase tracking-wide text-[var(--t-text-tertiary)]">
                          {{ trace.tool_name }} · {{ trace.summary }}
                        </p>
                      }
                    </div>
                  }
                  @if (msg.role === 'ai' && msg.proposed_actions?.length) {
                    <div class="space-y-2">
                      @for (action of msg.proposed_actions; track action.id) {
                        <div class="border border-[var(--t-border)] bg-[var(--t-bg)] p-4">
                          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Confirmation required</p>
                          <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ action.title }}</p>
                          <p class="mt-1 text-xs text-[var(--t-text-secondary)]">{{ action.description }}</p>
                          <button
                            type="button"
                            class="btn-primary mt-3 text-xs"
                            [disabled]="isTyping() || action.status !== 'draft'"
                            (click)="confirmAction(action)">
                            Confirm action
                          </button>
                        </div>
                      }
                    </div>
                  }
                  <p class="text-[10px] text-[var(--t-text-tertiary)] px-1" [class.text-right]="msg.role === 'user'">
                    {{ msg.timestamp | date:'HH:mm' }}
                    @if (msg.confidence) {
                      · {{ msg.confidence | percent:'1.0-0' }}
                    }
                  </p>
                </div>
              </div>
            </div>
          }

          @if (isTyping()) {
            <div class="flex">
              <div class="max-w-[80%] flex gap-4">
                <div class="w-8 h-8 rounded-lg bg-[var(--t-accent)] text-white flex items-center justify-center font-bold text-[10px]">AI</div>
                <div class="bg-[var(--t-accent-soft)] p-4 rounded-2xl rounded-tl-none flex gap-1 items-center h-10">
                  <span class="w-1.5 h-1.5 bg-[var(--t-accent)] rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                  <span class="w-1.5 h-1.5 bg-[var(--t-accent)] rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                  <span class="w-1.5 h-1.5 bg-[var(--t-accent)] rounded-full animate-bounce" style="animation-delay: 300ms"></span>
                </div>
              </div>
            </div>
          }
        </div>

        <!-- Input Area -->
        <div class="p-6 bg-[var(--t-bg)] border-t border-[var(--t-border)]">
          <form (submit)="sendMessage()" class="flex gap-4">
            <input type="text" 
                   [(ngModel)]="userInput" 
                   name="query"
                   placeholder="Ask anything about the portfolio..." 
                   class="input-field flex-1 !h-12 !text-base"
                   [disabled]="isTyping()">
            <button type="submit" 
                    [disabled]="!userInput.trim() || isTyping()"
                    class="btn-primary !h-12 px-6 flex items-center gap-2">
              <span>Send</span>
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </form>
        </div>
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; height: calc(100vh - 64px); }
  `]
})
export class AIInsightsComponent implements AfterViewChecked {
  private readonly api = inject(ApiService);
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  userInput = '';
  isTyping = signal(false);
  messages = signal<Message[]>([]);

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }

  sendMessage() {
    if (!this.userInput.trim() || this.isTyping()) return;

    const query = this.userInput.trim();
    this.userInput = '';
    
    this.messages.update(prev => [...prev, {
      role: 'user',
      content: query,
      timestamp: new Date()
    }]);

    this.isTyping.set(true);

    this.api.post<any>('/ai/chat', { query }).subscribe({
      next: (res) => {
        this.messages.update(prev => [...prev, {
          role: 'ai',
          content: res.response || 'No insight generated.',
          timestamp: new Date(),
          sources: res.sources || [],
          tool_trace: res.tool_trace || [],
          confidence: res.confidence,
          proposed_actions: res.proposed_actions || []
        }]);
        this.isTyping.set(false);
      },
      error: (err) => {
        this.messages.update(prev => [...prev, {
          role: 'ai',
          content: '<span class="text-red-500 font-bold">Error:</span> Failed to connect to AI agent. Please check backend logs.',
          timestamp: new Date()
        }]);
        this.isTyping.set(false);
      }
    });
  }

  clearChat() {
    this.messages.set([]);
  }

  confirmAction(action: ProposedAction) {
    if (this.isTyping() || action.status !== 'draft') return;
    this.isTyping.set(true);
    this.api.post<any>(`/ai/actions/${action.id}/confirm`, {}).subscribe({
      next: (res) => {
        action.status = res.status || 'confirmed';
        this.messages.update(prev => [...prev, {
          role: 'ai',
          content: res.message || 'Action confirmed.',
          timestamp: new Date(),
          sources: [{ label: 'Confirmed action', source_type: action.action_type }],
          tool_trace: [{
            tool_name: action.action_type,
            status: 'confirmed',
            summary: 'Executed through the underlying Transmuter API.',
            source_type: action.action_type
          }],
          confidence: 1
        }]);
        this.isTyping.set(false);
      },
      error: () => {
        this.messages.update(prev => [...prev, {
          role: 'ai',
          content: '<span class="text-red-500 font-bold">Error:</span> Failed to confirm action.',
          timestamp: new Date(),
          confidence: 0.4
        }]);
        this.isTyping.set(false);
      }
    });
  }
}
