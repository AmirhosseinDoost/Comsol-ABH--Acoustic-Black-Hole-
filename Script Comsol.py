import mph
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize

print("Starting COMSOL client...")
client = mph.start(cores=8)

model_path = 'Hook_2019.mph'
print(f"Loading model: {model_path}")
model = client.load(model_path)

# لیست‌ها برای ذخیره داده‌ها
all_iterations_data = []
optimal_data = []
profile_names = {1: "Power Law", 2: "Exponential", 3: "Trigonometric"}


def evaluate_reflection(params):
    length_abh, thickness_tip = params

    print(f"Evaluating -> l_abh: {length_abh * 1000:.1f} [mm], h_tip: {thickness_tip * 1000:.2f} [mm]")

    model.parameter('l_abh', f"{length_abh} [m]")
    model.parameter('h_tip', f"{thickness_tip} [m]")

    try:
        model.solve('Study 1')
        r_coeff = model.evaluate('abs(R_coeff)')
        mean_reflection = np.mean(r_coeff)

        # ثبت داده‌های هر گام
        all_iterations_data.append({
            'Profile Name': profile_names[PROFILE_TYPE],
            'l_abh [mm]': round(length_abh * 1000, 2),
            'h_tip [mm]': round(thickness_tip * 1000, 3),
            'Mean Reflection': round(mean_reflection, 5)
        })

        print(f"Result: Mean Reflection = {mean_reflection:.4f}")
        return mean_reflection

    except Exception as e:
        print("Solver failed (Geometry/Mesh error).")
        all_iterations_data.append({
            'Profile Name': profile_names[PROFILE_TYPE],
            'l_abh [mm]': round(length_abh * 1000, 2),
            'h_tip [mm]': round(thickness_tip * 1000, 3),
            'Mean Reflection': 1.0
        })
        return 1.0


x0 = np.array([0.07, 0.00071])
bounds = ((0.05, 0.10), (0.0005, 0.002))

# ----------------- بخش بهینه‌سازی -----------------
for PROFILE_TYPE in [1, 2, 3]:
    print("\n==================================================")
    print(f"   STARTING OPTIMIZATION FOR PROFILE TYPE: {PROFILE_TYPE}")
    print("==================================================")

    model.parameter('Profile_Type', str(PROFILE_TYPE))
    model.parameter('l_abh', f"{x0[0]} [m]")
    model.parameter('h_tip', f"{x0[1]} [m]")

    result = minimize(evaluate_reflection, x0, method='Nelder-Mead', bounds=bounds,
                      options={'disp': True, 'maxiter': 100})

    status_msg = "Converged" if result.success else "Not Converged (Best Found)"
    print(f"\n--- Optimization Finished for Profile {PROFILE_TYPE} ({status_msg}) ---")

    model.parameter('l_abh', f"{result.x[0]} [m]")
    model.parameter('h_tip', f"{result.x[1]} [m]")
    save_name = f'ABH_Profile{PROFILE_TYPE}_Optimized.mph'
    model.save(save_name)
    print(f"Saved optimized model as '{save_name}'")

    optimal_data.append({
        'Profile ID': PROFILE_TYPE,
        'Profile Name': profile_names[PROFILE_TYPE],
        'Optimal l_abh [mm]': round(result.x[0] * 1000, 2),
        'Optimal h_tip [mm]': round(result.x[1] * 1000, 2),
        'Min Mean Reflection': round(result.fun, 4),
        'Status': status_msg
    })

# ----------------- بخش استخراج اکسل و رسم نمودار -----------------
if optimal_data and all_iterations_data:
    # ۱. ذخیره فایل اکسل
    excel_filename = 'ABH_Optimization_Results.xlsx'
    df_all = pd.DataFrame(all_iterations_data)
    df_optimal = pd.DataFrame(optimal_data)

    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df_all.to_excel(writer, sheet_name='All_Evaluations', index=False)
        df_optimal.to_excel(writer, sheet_name='Optimal_Results', index=False)

    print("\n==================================================")
    print("             FINAL COMPARISON SUMMARY               ")
    print("==================================================")
    print(df_optimal.to_string(index=False))
    print(f"\n✅ Results successfully saved to '{excel_filename}'")

    # ۲. رسم نمودار پراکندگی
    print("Generating scatter plots...")
    df_filtered = df_all[df_all['Mean Reflection'] < 1.0].copy()

    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    fig.suptitle('Optimization Search Space: ABH Length vs Tip Thickness', fontsize=16, fontweight='bold', y=1.05)

    profiles = ['Power Law', 'Exponential', 'Trigonometric']
    cmaps = 'viridis_r'

    for i, profile in enumerate(profiles):
        ax = axes[i]
        data = df_filtered[df_filtered['Profile Name'] == profile]

        if not data.empty:
            sc = ax.scatter(data['l_abh [mm]'], data['h_tip [mm]'],
                            c=data['Mean Reflection'], cmap=cmaps,
                            s=60, edgecolors='black', alpha=0.8)

            # هایلایت نقطه بهینه
            min_idx = data['Mean Reflection'].idxmin()
            opt_point = data.loc[min_idx]
            ax.scatter(opt_point['l_abh [mm]'], opt_point['h_tip [mm]'],
                       color='red', marker='*', s=300, edgecolors='black',
                       label=f"Optimum: {opt_point['Mean Reflection']:.4f}")

            ax.set_title(f'{profile} Profile', fontsize=14)
            ax.set_xlabel('l_abh [mm]', fontsize=12)
            if i == 0:
                ax.set_ylabel('h_tip [mm]', fontsize=12)

            ax.grid(True, linestyle='--', alpha=0.5)
            ax.legend(loc='upper right')
            cbar = plt.colorbar(sc, ax=ax)
            cbar.set_label('Mean Reflection Coefficient', fontsize=10)

    plt.tight_layout()
    image_path = 'ABH_Optimization_Scatter.png'
    plt.savefig(image_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"✅ Scatter plot successfully saved to '{image_path}'")

else:
    print("No data was generated.")

client.disconnect()