// A stand-in for XMLHttpRequest that lets a test step through an upload:
// progress events, the moment the whole file has been sent, and the reply.
export class FakeUpload {
  static last: FakeUpload | null = null;
  method = "";
  url = "";
  headers: Record<string, string> = {};
  body: FormData | null = null;
  status = 0;
  responseText = "";
  upload: { onprogress: ((e: object) => void) | null; onload: (() => void) | null } = {
    onprogress: null,
    onload: null,
  };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }

  send(body: FormData) {
    this.body = body;
    FakeUpload.last = this;
  }

  progress(loaded: number, total: number) {
    this.upload.onprogress?.({ lengthComputable: true, loaded, total });
  }

  sent() {
    this.upload.onload?.();
  }

  respond(status: number, body: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.onload?.();
  }
}

export function installFakeUpload() {
  FakeUpload.last = null;
  global.XMLHttpRequest = FakeUpload as unknown as typeof XMLHttpRequest;
}
