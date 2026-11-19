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
		(ontable red)
		(clear red)
		(ontable green)
		(on purple green)
		(clear purple)

		(ontable blue)
		(on yellow blue)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable blue)
		(clear blue)
		(ontable yellow)
		(on orange yellow)
		(clear orange)

		(ontable red)
		(on green red)
		(on purple green)
		(clear purple)
	))
)