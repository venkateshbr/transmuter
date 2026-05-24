import { Injectable, computed, signal } from '@angular/core';

const LOADING_MESSAGES = [
  'Preparing your workspace view...',
  'Syncing the latest portfolio signals...',
  'Fetching the numbers so you do not have to...',
  'Rebuilding the executive view...',
  'Checking initiatives, actions, and financials...',
  'This is a good moment to triage one email.',
  'Coffee-compatible loading in progress.',
  'Pulling the threads together...',
  'Refreshing your transformation cockpit...',
  'Loading the latest truth from the system...',
  'Pulling the latest transformation data together...',
  'Almost there. Aligning the moving parts...',
] as const;

@Injectable({ providedIn: 'root' })
export class LoadingService {
  private readonly pendingRequests = signal(0);
  private readonly navigating = signal(false);
  private readonly reveal = signal(false);
  private readonly progressValue = signal(0);
  private readonly messageValue = signal<string>(LOADING_MESSAGES[0]);
  private revealTimer: ReturnType<typeof setTimeout> | null = null;
  private progressTimer: ReturnType<typeof setInterval> | null = null;
  private messageTimer: ReturnType<typeof setInterval> | null = null;

  readonly active = computed(() => this.pendingRequests() > 0 || this.navigating());
  readonly visible = computed(() => this.reveal() && this.active());
  readonly progress = computed(() => this.progressValue());
  readonly message = computed(() => this.messageValue());

  beginRequest(): void {
    this.pendingRequests.update(count => count + 1);
    this.scheduleReveal();
  }

  endRequest(): void {
    this.pendingRequests.update(count => Math.max(0, count - 1));
    this.finishIfIdle();
  }

  beginNavigation(): void {
    this.navigating.set(true);
    this.scheduleReveal();
  }

  endNavigation(): void {
    this.navigating.set(false);
    this.finishIfIdle();
  }

  private scheduleReveal(): void {
    if (this.reveal() || this.revealTimer) return;
    this.progressValue.set(Math.max(this.progressValue(), 12));
    this.messageValue.set(this.nextMessage());
    this.revealTimer = setTimeout(() => {
      this.revealTimer = null;
      if (!this.active()) return;
      this.reveal.set(true);
      this.startProgress();
      this.startMessageRotation();
    }, 160);
  }

  private startProgress(): void {
    if (this.progressTimer) return;
    this.progressTimer = setInterval(() => {
      if (!this.active()) return;
      const current = this.progressValue();
      const next = current < 70 ? current + 7 : current < 88 ? current + 2 : current + 0.5;
      this.progressValue.set(Math.min(94, next));
    }, 220);
  }

  private startMessageRotation(): void {
    if (this.messageTimer) return;
    this.messageTimer = setInterval(() => {
      if (!this.active()) return;
      this.messageValue.set(this.nextMessage(this.messageValue()));
    }, 6500);
  }

  private finishIfIdle(): void {
    if (this.active()) return;
    if (this.revealTimer) {
      clearTimeout(this.revealTimer);
      this.revealTimer = null;
    }
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }
    if (this.messageTimer) {
      clearInterval(this.messageTimer);
      this.messageTimer = null;
    }
    if (!this.reveal()) {
      this.progressValue.set(0);
      return;
    }
    this.progressValue.set(100);
    setTimeout(() => {
      if (this.active()) return;
      this.reveal.set(false);
      this.progressValue.set(0);
    }, 180);
  }

  private nextMessage(previous?: string): string {
    const candidates = previous
      ? LOADING_MESSAGES.filter(message => message !== previous)
      : LOADING_MESSAGES;
    return candidates[Math.floor(Math.random() * candidates.length)];
  }
}
