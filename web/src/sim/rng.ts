/**
 * 遊戲內隨機選取（與桌面版 `random.Random` 用法對應：choice／sample／shuffle／uniform）。
 * 未固定種子；僅保證與 Python 相同的**池與流程**，不保證逐位元相同序列。
 */
export class SimRng {
  /** @returns [0,1) 均勻亂數 */
  random(): number {
    return Math.random();
  }

  /**
   * @param arr - 非空陣列
   * @returns 隨機一筆
   */
  choice<T>(arr: readonly T[]): T {
    if (arr.length === 0) {
      throw new Error("SimRng.choice: empty array");
    }
    const i = Math.floor(this.random() * arr.length);
    return arr[i] as T;
  }

  /**
   * 不重複抽樣（類似 `random.sample`）。
   *
   * @param arr - 來源
   * @param k - 抽取數量
   */
  sample<T>(arr: readonly T[], k: number): T[] {
    const copy = [...arr];
    this.shuffle(copy);
    return copy.slice(0, Math.min(k, copy.length));
  }

  /**
   * Fisher–Yates 洗牌（原地）。
   *
   * @param arr - 可變陣列
   */
  shuffle<T>(arr: T[]): void {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(this.random() * (i + 1));
      const t = arr[i];
      arr[i] = arr[j] as T;
      arr[j] = t as T;
    }
  }

  /**
   * @param a - 下限（含）
   * @param b - 上限（不含，與 Python `uniform` 一致）
   */
  uniform(a: number, b: number): number {
    return a + this.random() * (b - a);
  }
}
