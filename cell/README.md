# 肝臟細胞核值比計算
## 環境設置
1. python 3.12.10
1. opencv-python 4.12.0.88
1. pillow 11.0.0
1. pytorch 2.7.1+cu128
1. torchvision 0.22.1
1. pandas 2.3.0
1. cuda 12.8
需要安裝cuda  
## 流程圖
![圖片](/cell/流程圖.jpg)
## 使用方法
先下載模型參數<br>
stage1模型參數 https://drive.google.com/file/d/1XNjVBBhplQ0WfAXGde6miDq-deYH4gTz/view?usp=sharing <br>
stage2模型參數 https://drive.google.com/file/d/1tXKcYGA_5wFxG2nL_ByL_E4cYYiAj3U8/view?usp=sharing <br>
下載後解壓到cell資料夾下

```
# 在專案根目錄執行
python -m cell.main --mix_dir 圖片位置
#example python -m cell.main --mix_dir cell/4/4_channel_mix.tif
```
會在sample資料夾產生每個細胞的細胞質分割範圍（檔名為細胞編號）<br>
![圖片](/cell/sample/0.jpg)<br>
會在test資料夾產生整張圖片細胞的細胞質分割範圍（每個細胞標上編號）和csv檔。test.csv 每列為一個細胞（編號、座標、細胞核面積、細胞質面積、核質比），test_summary.csv 為平均值
![圖片](/cell/test/test.jpg)<br>
## 實驗結果
![圖片](/cell/result.jpg)<br>
