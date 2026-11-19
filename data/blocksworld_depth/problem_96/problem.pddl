(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(on green yellow)
		(clear green)

		(ontable blue)
		(on purple blue)
		(on red purple)
		(clear red)
	)
	(:goal (and (handempty robot)
		(ontable yellow)
		(clear yellow)
		(ontable orange)
		(on purple orange)
		(clear purple)

		(ontable green)
		(on red green)
		(on blue red)
		(clear blue)
	))
)